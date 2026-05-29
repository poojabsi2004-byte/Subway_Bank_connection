from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import datetime, base64
from datetime import timedelta
import paramiko

class BSIBankFile(models.Model):
    _name = "bsi.sftp.files"
    _description = "BSI Bank File"
    _rec_name = "file_name"
    
    file_name = fields.Char(string="File name")
    download_file = fields.Binary(string="Download File")
    statement_id = fields.One2many('bsi.store.bank.statements', 'file_id', string="Statements")
    state = fields.Selection([('draft', 'Draft'), ('fetched', 'Fatched'), ('statements', 'Statements')], default="draft")
    
    def sftp_connection(self):
        username = self.env['ir.config_parameter'].sudo().get_param('bsi_bank_connection.sftp_username')
        password = self.env['ir.config_parameter'].sudo().get_param('bsi_bank_connection.sftp_password')

        if not username or not password:
            raise ValidationError("SFTP account credentials could not be fetched.")

        host = '178.156.207.111'
        port = 22
        remote_path = 'incoming'

        transport = None
        sftp = None

        try:
            transport = paramiko.Transport((host, port))
            transport.banner_timeout = 30
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            files = sftp.listdir(remote_path)

            existing_files = self.env['bsi.sftp.files'].sudo().search([]).mapped('file_name')

            for filename in files:
                if not filename.endswith('.txt'):
                    continue
                if filename in existing_files:
                    print(f"====== Skipping already fetched file: {filename} ======")
                    continue

                file_path = f"{remote_path}/{filename}"

                # read the REAL file content so it can be downloaded later
                with sftp.open(file_path, 'rb') as fh:
                    raw_data = fh.read()

                self.env['bsi.sftp.files'].sudo().create({
                    'file_name': filename,
                    'download_file': base64.b64encode(raw_data),   # actual file content
                    'state': 'fetched',
                })

        except Exception as e:
            raise UserError("SFTP Error: %s" % str(e))
        finally:
            if sftp:
                sftp.close()
            if transport:
                transport.close()

        return True
    
    def generate_statement(self):
        if not self:
            raise ValidationError("Please select a file to generate statements.")

        AccountModel   = self.env['bsi.store.bank.accounts'].sudo()
        StatementModel = self.env['bsi.store.bank.statements'].sudo()

        processed_file_ids = []

        for rec in self:
            if not rec.file_name:
                raise ValidationError("File name is missing for one of the selected records.")

            if not rec.download_file:
                raise ValidationError("File '%s' has no content. Please fetch it again." % rec.file_name)

            # ── 1. Read file content from the stored binary ──────────────────────
            file_data = base64.b64decode(rec.download_file).decode('utf-8', errors='ignore')

            if not file_data.strip():
                raise ValidationError("File '%s' is empty." % rec.file_name)

            print("====== file_data ======", file_data)

            # ── 2. Parse — collect accounts + the statement date from THIS file ──
            file_accounts      = {}     # { account_number: {fields} }
            current_group_date = None

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
                    if acc_no and acc_no not in file_accounts:
                        file_accounts[acc_no] = {
                            'account_number': acc_no,
                            'account_name':   acc_name,
                        }

            print(f"====== Collected {len(file_accounts)} accounts ======", file_accounts)

            if current_group_date is None:
                current_group_date = fields.Date.today()

            # ── 3. Create only missing accounts (build account_map) ──────────────
            existing_db_accounts = AccountModel.search([
                ('account_number', 'in', list(file_accounts.keys())),
            ])
            existing_account_numbers = set(existing_db_accounts.mapped('account_number'))

            account_map = {}   # account_number → account record

            for acc_no, acc_data in file_accounts.items():
                if acc_no in existing_account_numbers:
                    acc_rec = existing_db_accounts.filtered(lambda a: a.account_number == acc_no)
                    account_map[acc_no] = acc_rec
                    print(f"SKIP account (already exists): {acc_no}")

                    if not acc_rec.account_name and acc_data.get('account_name'):
                        acc_rec.account_name = acc_data['account_name']
                else:
                    new_acc = AccountModel.create({
                        'account_number': acc_data['account_number'],
                        'account_name':   acc_data['account_name'],
                    })
                    account_map[acc_no] = new_acc
                    print(f"CREATED account: {acc_no} | name: {acc_data['account_name']}")

            # ── 4. Create one statement per account for THIS file ────────────────
            for acc_no, acc_rec in account_map.items():
                existing_statement = StatementModel.search([
                    ('account_id', '=', acc_rec.id),
                    ('file_id', '=', rec.id),
                ], limit=1)

                if existing_statement:
                    print(f"SKIP statement (already exists): acc={acc_no}")
                else:
                    StatementModel.create({
                        'account_id':       acc_rec.id,
                        'transaction_date': current_group_date,
                        'file_id':          rec.id,
                    })
                    print(f"CREATED statement: acc={acc_no} | file={rec.file_name}")

            rec.state = 'statements'
            processed_file_ids.append(rec.id)

        if not processed_file_ids:
            raise ValidationError("No files were processed.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Statements',
            'res_model': 'bsi.store.bank.statements',
            'view_mode': 'list,form',
            'domain': [('file_id', 'in', processed_file_ids)],
            'target': 'current',
        }