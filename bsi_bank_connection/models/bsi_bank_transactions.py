# -*- coding: utf-8 -*-
from odoo import fields, models, api

class BSIBankAccountTransaction(models.Model):
    _name = "bsi.bank.transactions"
    _description = "BSI Bank Accounts Transaction"
    _rec_name = 'account_id'

    account_id = fields.Many2one("bsi.store.bank.accounts",string="Account")
    store_id = fields.Many2one(related="account_id.store_id", string="Store", store=True, readonly=True)
    store_scheduling = fields.Many2many('store.scheduling',string="Store schuduling")
    transaction_date = fields.Date("Transaction Date")
    type_code = fields.Char(string="Type Code")
    transaction_type = fields.Char(string="Transaction Type")
    fund_type = fields.Char(string='Fund Type')
    amount = fields.Float(string="Amount")
    description = fields.Char(string="Description")
