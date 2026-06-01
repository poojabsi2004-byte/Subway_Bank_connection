# -*- coding: utf-8 -*-
from odoo import api, models, fields,_


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	week_automation_count = fields.Integer(string="Week Automation Count", default=1, config_parameter='bsi_subway_base.week_automation_count')
	post_message_in_emp = fields.Boolean(string="Post Log Msgs in Employee?", default=False, config_parameter='bsi_subway_base.post_message_in_emp')
