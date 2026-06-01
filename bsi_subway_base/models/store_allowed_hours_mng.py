# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StoreActualHours(models.Model):
	_name = 'store.actual.hours'
	_description = 'Store Actual Hours'

	week_actual_hours = fields.Float(string="Allowed Hours")
	week_actual_sale = fields.Float(string="Weekly Sales")
