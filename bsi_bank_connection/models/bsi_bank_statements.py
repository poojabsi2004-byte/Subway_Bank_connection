# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
import datetime, base64
from datetime import timedelta, date
import paramiko

class BSIBankStatement(models.Model):
    _name = "bsi.store.bank.statements"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "BSI Bank Statements"
    _rec_name = "account_id"

    account_id = fields.Many2one('bsi.store.bank.accounts', string="Account Number", tracking=True)
    store_id = fields.Many2one(related="account_id.store_id", string="Store", store=True, readonly=False)
    transaction_date = fields.Date(string="Transaction Date")
    amount = fields.Float(string="Amount")
    transaction_ids = fields.Many2many('bsi.bank.transactions', string="Transactions")
    file_id = fields.Many2one('bsi.sftp.files', string='File', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('transactions', 'Transactions'),('data_updated', 'Data Updated'), ('error', 'Error')],  default="draft", tracking=True)
    error = fields.Char(string="Error")
    
    def generate_transactions(self):
        CREDIT_CODES = {'142', '301', '303', '304', '306', '195', '399'}

        TransactionModel = self.env['bsi.bank.transactions'].sudo()
        AccountModel     = self.env['bsi.store.bank.accounts'].sudo()

        for rec in self:
            # ── 1. Get the linked file and its stored content ────────────────────
            if not rec.file_id or not rec.file_id.file_name:
                raise ValidationError("Statement '%s' has no linked file." % rec.display_name)

            if not rec.file_id.download_file:
                raise ValidationError(
                    "File '%s' has no content. Please fetch it again." % rec.file_id.file_name
                )

            if not rec.account_id:
                raise ValidationError("Statement has no linked account.")

            file_name           = rec.file_id.file_name
            stmt_account_number = rec.account_id.account_number

            # ── 2. Read file content from the stored binary ──────────────────────
            file_data = base64.b64decode(rec.file_id.download_file).decode('utf-8', errors='ignore')

            if not file_data.strip():
                raise ValidationError("File '%s' is empty." % file_name)

            # ── 3. Parse file — collect transactions ─────────────────────────────
            file_accounts     = {}    # { account_number: {...} }
            file_transactions = []    # [ {account_number, type_code, amount, ...} ]

            current_group_date = None
            scan_account       = None

            for raw_line in file_data.splitlines():
                line  = raw_line.strip().rstrip('/')
                parts = line.split(',')
                if not parts:
                    continue

                rt = parts[0]

                if rt == '02':
                    if len(parts) > 4 and parts[4]:
                        rd = parts[4]
                        try:
                            current_group_date = datetime.date(
                                int('20' + rd[0:2]), int(rd[2:4]), int(rd[4:6])
                            )
                        except Exception:
                            current_group_date = fields.Date.today()
                    else:
                        current_group_date = fields.Date.today()

                elif rt == '03':
                    acc_no   = parts[1].strip() if len(parts) > 1 else ''
                    acc_name = parts[2].strip() if len(parts) > 2 else ''
                    if acc_no:
                        scan_account = acc_no
                        if acc_no not in file_accounts:
                            file_accounts[acc_no] = {
                                'account_number': acc_no,
                                'account_name':   acc_name,
                            }

                elif rt == '16' and scan_account:
                    type_code  = parts[1].strip() if len(parts) > 1 else ''
                    raw_amount = parts[2].strip() if len(parts) > 2 else '0'
                    fund_type  = parts[3].strip() if len(parts) > 3 else ''
                    amount     = round(float(raw_amount or 0) / 100, 2)
                    trx_date   = current_group_date

                    try:
                        if fund_type == 'V' and len(parts) > 4 and parts[4]:
                            rd = parts[4]
                            trx_date = datetime.date(
                                int('20' + rd[0:2]), int(rd[2:4]), int(rd[4:6])
                            )
                    except Exception:
                        trx_date = current_group_date

                    description = parts[6].strip() if len(parts) > 6 else ''

                    file_transactions.append({
                        'account_number':   scan_account,
                        'type_code':        type_code,
                        'amount':           amount,
                        'transaction_date': trx_date,
                        'description':      description,
                        'fund_type':        fund_type,
                        'transaction_type': 'credit' if type_code in CREDIT_CODES else 'debit',
                    })

                elif rt == '49':
                    scan_account = None

            print(f"====== Parsed: {len(file_accounts)} accounts, {len(file_transactions)} transactions ======")

            # ── 4. Make sure this statement's account is in the file ─────────────
            if stmt_account_number not in file_accounts:
                raise ValidationError(
                    "Account '%s' linked to this statement was not found in file '%s'."
                    % (stmt_account_number, file_name)
                )

            # ── 5. Keep only transactions for THIS account + statement date ──────
            account_transactions = [
                txn for txn in file_transactions
                if txn['account_number'] == stmt_account_number
                and txn['transaction_date'] == rec.transaction_date
            ]

            print(f"====== Transactions for {stmt_account_number} on {rec.transaction_date}: "
                f"{len(account_transactions)} ======")

            # ── 6. Find the account record ───────────────────────────────────────
            acc_rec = AccountModel.search([
                ('account_number', '=', stmt_account_number),
            ], limit=1)

            if not acc_rec:
                raise ValidationError("Account '%s' not found in database." % stmt_account_number)

            # ── 7. Existing transactions for this account + date (dedup) ─────────
            existing_db_txns = TransactionModel.search([
                ('account_id', '=', acc_rec.id),
                ('transaction_date', '=', rec.transaction_date),
            ])

            def txn_key(account_id, date, type_code, amount, fund_type):
                return (account_id, str(date), type_code, round(float(amount), 2), fund_type)

            existing_txn_keys = {
                txn_key(t.account_id.id, t.transaction_date, t.type_code, t.amount, t.fund_type)
                for t in existing_db_txns
            }

            # ── 8. Create only missing transactions ──────────────────────────────
            new_txn_ids = []

            for txn in account_transactions:
                key = txn_key(
                    acc_rec.id, txn['transaction_date'], txn['type_code'],
                    txn['amount'], txn['fund_type'],
                )

                if key in existing_txn_keys:
                    print(f"SKIP (exists): date={txn['transaction_date']} "
                        f"type={txn['type_code']} amount={txn['amount']}")
                else:
                    new_txn = TransactionModel.create({
                        'account_id':       acc_rec.id,
                        'transaction_date': txn['transaction_date'],
                        'type_code':        txn['type_code'],
                        'transaction_type': txn['transaction_type'],
                        'fund_type':        txn['fund_type'],
                        'amount':           txn['amount'],
                        'description':      txn['description'],
                    })
                    existing_txn_keys.add(key)
                    new_txn_ids.append(new_txn.id)
                    print(f"CREATED: date={txn['transaction_date']} "
                        f"type={txn['type_code']} amount={txn['amount']}")

            # ── 9. Link all transactions (existing + new) to this statement ──────
            all_txn_ids = existing_db_txns.ids + new_txn_ids
            rec.transaction_ids = [(6, 0, all_txn_ids)]
            rec.state = 'transactions'

            print(f"====== Statement {rec.display_name} [{rec.transaction_date}]: "
                f"{len(new_txn_ids)} created, {len(existing_db_txns)} existed, "
                f"{len(all_txn_ids)} linked ======")

        return True
        
    def update_food_cost(self):
        print("-------update_food_cost--------")

    def update_payroll(self):
        print("-------update_payroll--------")
    

    def update_both_foodcost_payroll(self):
        Scheduling  = self.env['store.scheduling']
        Mapping     = self.env['bsi.mapping'].sudo()
        Transaction = self.env['bsi.bank.transactions'].sudo()

        for rec in self:
            print("\n===== UPDATE BOTH — statement", rec.id, "=====")
            
            store = rec.account_id.store_id if rec.account_id else None
            if not store:
                msg = ("Store is not set for this statement's account. "
                    "Please assign a store and try again.")
                rec.write({'state': 'error', 'error': msg})
                rec.message_post(body="Update both stopped: %s" % msg)
                print("FAIL: no store")
                break

            account_transactions = Transaction.search([('account_id', '=', rec.account_id.id)])
            print("transactions:", len(account_transactions))
            if not account_transactions:
                msg = "No transactions found for account '%s'." % (rec.account_id.account_number or '')
                rec.write({'state': 'error', 'error': msg})
                rec.message_post(body=msg)
                continue
            
            store_schedulings = Scheduling.sudo().search([('store_id', '=', store.id)])
            print("scheduling weeks:", len(store_schedulings))
            if not store_schedulings:
                msg = "No store scheduling records found for store '%s'." % store.display_name
                rec.write({'state': 'error', 'error': msg})
                rec.message_post(body=msg)
                continue

            mappings = Mapping.search([('account_id', '=', rec.account_id.id)])
            if mappings:
                default_prev_week = 1
                print("CASE 1: account-specific mappings:", len(mappings))
            else:
                mappings = Mapping.search([('account_id', '=', False)])
                default_prev_week = 0
                print("CASE 2: generic mappings:", len(mappings))
                if not mappings:
                    msg = "Account not mapped and no generic mappings found — nothing to update."
                    rec.write({'state': 'error', 'error': "Account not mapped and no generic mappings found nothing to update."})
                    rec.message_post(body=msg)
                    print(msg)
                    continue

            rec.message_post(
                body="Starting <b>Update both</b> for account <b>%s</b> (store: %s) "
                    "%s transactions, %s scheduling weeks, %s mapping rule(s)."
                    % (rec.account_id.account_number, store.display_name,
                        len(account_transactions), len(store_schedulings), len(mappings))
            )
            account_transactions.write({'store_scheduling': [(5, 0, 0)]})
            update_log = []
            for mapping in mappings:
                keyword       = str(mapping.keyword or '').strip()
                field_name    = str(mapping.field_name or '').strip()
                previous_week = int(mapping.previous_week or default_prev_week)
                print(f"  mapping {mapping.id}: keyword='{keyword}' field='{field_name}' prev_week={previous_week}")

                if not keyword or not field_name:
                    raise ValidationError(
                        "Mapping (ID %s) is missing a keyword or field name. "
                        "Please complete the mapping before running this update." % mapping.id
                    )

                if field_name not in Scheduling._fields:
                    raise ValidationError(
                        "Field name '%s' in mapping (ID %s) does not exist on store scheduling. "
                        "Please correct the mapping." % (field_name, mapping.id)
                    )

                matched = [t for t in account_transactions if keyword in str(t.description or '').strip()]
                print(f"    matched txns for '{keyword}':", len(matched))
                if not matched:
                    continue
                amounts_by_week = {}
                store_scheduling_by_txn = {}
                
                for t in matched:
                    if not t.transaction_date:
                        continue

                    week = Scheduling.sudo().search([
                        ('store_id',           '=', store.id),
                        ('week_starting_date', '<=', t.transaction_date),
                        ('week_ending_date',   '>=', t.transaction_date),
                    ], limit=1)
                    if not week:
                        print(f"    txn {t.transaction_date}: no scheduling week contains it")
                        continue

                    end_date = week.week_ending_date
                    weekday  = end_date.weekday()
                    if weekday < 2:
                        adjusted_week_end = end_date - timedelta(days=weekday + 3)
                    else:
                        adjusted_week_end = end_date - timedelta(days=weekday - 2)

                    iso_year, current_week_num, _ = adjusted_week_end.isocalendar()
                    amount = t.amount or 0.0

                    if not previous_week: 
                        target_week = self._get_week_name(current_week_num, iso_year, offset=0)
                        amounts_by_week[target_week] = amounts_by_week.get(target_week, 0.0) + amount
                        store_scheduling_by_txn.setdefault(t.id, set()).add(target_week)
                    else:
                        split_amount = amount / previous_week
                        for i in range(1, previous_week + 1):
                            target_week = self._get_week_name(current_week_num, iso_year, offset=i)
                            amounts_by_week[target_week] = amounts_by_week.get(target_week, 0.0) + split_amount
                            store_scheduling_by_txn.setdefault(t.id, set()).add(target_week)

                print("    amounts_by_week:", amounts_by_week)

                for week_name, amount in amounts_by_week.items():
                    target = Scheduling.sudo().search([
                        ('store_id',             '=', store.id),
                        ('combination_rec_name', '=', week_name),
                    ], limit=1)
                    if not target:
                        print(f"    no scheduling record for '{week_name}'")
                        continue

                    target.sudo().write({field_name: amount})
                
                    print(f"    WROTE {week_name}.{field_name} = {amount}")
                    update_log.append("%s → %s = %.2f (keyword: '%s')"
                                    % (week_name, field_name, amount, keyword))
                   
                    txn_ids_for_this_week = [
                        txn_id for txn_id, weeks in store_scheduling_by_txn.items()
                        if week_name in weeks
                    ]
                    if txn_ids_for_this_week:
                        Transaction.browse(txn_ids_for_this_week).write({
                            'store_scheduling': [(4, target.id)]
                        })
                        print(f"    LINKED scheduling {week_name} → txn ids {txn_ids_for_this_week}")
                        print(f"  store_scheduling_by_txn  {store_scheduling_by_txn}")

            if update_log:
                rec.write({'state': 'data_updated', 'error': False})
                rec.message_post(body="Update both completed.\n" .join(update_log))
                print("DONE — data_updated")
            else:
                msg = ("No matching transactions found for account '%s'. "
                    "Check that the mapping keyword appears in the transaction descriptions, "
                    "and that the transaction dates fall within the store's scheduling weeks."
                    % rec.account_id.account_number)
                rec.write({'state': 'error', 'error': msg})
                rec.message_post(body=msg)
                print("DONE — no match, state=error")


    def _get_week_name(self, week_num, iso_year, offset=1):
        """Return week label like 'W20 2026', handling year boundary rollover."""
        target_week = week_num - offset
        if target_week < 1:
            prev_year = iso_year - 1
            last_week_prev_year = date(prev_year, 12, 28).isocalendar()[1]
            target_week = last_week_prev_year + target_week
            return f'W{target_week} {prev_year}'
        return f'W{target_week} {iso_year}'
