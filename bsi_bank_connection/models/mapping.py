# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
import datetime, base64
from datetime import timedelta, date
import paramiko

class BSIMapping(models.Model):
    _name = "bsi.mapping"
    _description = "Mapping"
    _rec_name = 'keyword'

    account_id = fields.Many2one('bsi.store.bank.accounts', string="Account")
    keyword = fields.Char(string="Keyword", required=True)
    field_name = fields.Char(string="Field Name", required=True)
    previous_week = fields.Float(string="Previous Week")
    previous_day = fields.Float(string="Previous Day")

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if not self.account_id:
            return

        store = self.account_id.store_id

        print(f"====== store: {store} ======")
        print(f"====== store.place_type_id: {store.place_type_id} ======")

        if not store:
            self.previous_day = 0
            return

        if not store.place_type_id:
            self.previous_day = 0
            return

        place_type = store.place_type_id
        print(f"====== place_type: {place_type.name} ======")
        print(f"====== scheduling_week_start_day: {place_type.scheduling_week_start_day} ======")

        self.previous_day = float(place_type.scheduling_week_start_day or 0)
