# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import datetime, base64
from datetime import timedelta
import paramiko

class BSIBankAccount(models.Model):
    _name = "bsi.store.bank.accounts"
    _description = "BSI Bank Accounts"
    _rec_name = "account_number"
    
    account_number = fields.Char(string="Account Number")
    store_id = fields.Many2one('store.store', string="Store")
    # store_scheduling = fields.Many2one('store.scheduling', string="Store")
    account_name = fields.Char(string="Account Name")
    transaction_ids = fields.One2many('bsi.bank.transactions','account_id',string="Transactions")
    transaction_date = fields.Date(related='transaction_ids.transaction_date',string="Date")

    
    def generate_transactions(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bsi.bank.transactions',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.transaction_ids.ids)],
            'target': 'current',
            'context': {
                'default_account_id': self.id,
            },
        }
