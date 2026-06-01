# -*- coding: utf-8 -*-
from odoo import api, models, fields,_
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import ValidationError, AccessError, UserError

class StoreScheduling(models.Model):
	_inherit = "store.scheduling"

	# Scheduler for Four Week Automation
	def three_week_temporary_schedular(self):
		today_date = datetime.now().date()
		current_week_records = self.env['store.scheduling'].search([('week_starting_date','<=',today_date),('week_ending_date','>=',today_date)])
		for current_week in current_week_records:
			current_week_ending_date = current_week.week_ending_date
			start_date = current_week_ending_date + timedelta(days=1)
			for rec in range(1, 4):
				end_date = start_date + timedelta(days=6)
				vals = {
					'store_id': current_week.store_id.id,
					'week_starting_date': start_date,
					'week_ending_date': end_date,
				}
				bsi_store_id = self.env['store.scheduling'].search([('week_starting_date', '=', start_date),
					('week_ending_date', '=', end_date), ('store_id', '=', current_week.store_id.id)])
				if not bsi_store_id:
					bsi_store_id = self.env['store.scheduling'].create(vals)
				start_date = start_date + timedelta(days=7)

	# Scheduler for every week Automation
	# Updated with res.config configuration add number of weeks to be created.
	def every_week_automation(self):
		today_date = datetime.now().date()
		current_week_records = self.env['store.scheduling'].search([('week_starting_date','<=',today_date),('week_ending_date','>=',today_date)])
		for current_week in current_week_records:
			next_week_starting_date = current_week.week_starting_date
			next_week_ending_date = current_week.week_ending_date

			previous_week_starting_date = current_week.week_starting_date
			previous_week_ending_date = current_week.week_ending_date

			no_of_weeks = 1
			temp_no_of_weeks = self.env['ir.config_parameter'].sudo().get_param('bsi_subway_base.week_automation_count')

			if temp_no_of_weeks is not False:
				if int(temp_no_of_weeks) != 0:
					no_of_weeks = int(temp_no_of_weeks)

			for num in range(1, no_of_weeks+1):
				next_week_starting_date = next_week_starting_date + timedelta(days=7)
				next_week_ending_date = next_week_ending_date + timedelta(days=7)

				previous_week_starting_date = previous_week_starting_date - timedelta(days=7)
				previous_week_ending_date = previous_week_ending_date - timedelta(days=7)


				next_scheduling_id = self.env['store.scheduling'].search([('store_id', '=', current_week.store_id.id), 
					('week_starting_date','=',next_week_starting_date), ('week_ending_date','=',next_week_ending_date)])
				if not next_scheduling_id:
					vals = {
					'store_id': current_week.store_id.id,
					'week_starting_date': next_week_starting_date,
					'week_ending_date': next_week_ending_date,
					}
					next_scheduling_id = self.env['store.scheduling'].create(vals)

				previous_scheduling_id = self.env['store.scheduling'].search([('store_id', '=', current_week.store_id.id), 
					('week_starting_date','=',previous_week_starting_date), ('week_ending_date','=',previous_week_ending_date)])
				if not previous_scheduling_id:
					vals = {
					'store_id': current_week.store_id.id,
					'week_starting_date': previous_week_starting_date,
					'week_ending_date': previous_week_ending_date,
					}
					previous_scheduling_id = self.env['store.scheduling'].create(vals)

	# Scheduler for Readonly data 
	def readonly_data_when_user_is_not_admin(self):
		today_date = datetime.now().date()
		current_week_records = self.env['store.scheduling'].search([('week_starting_date','<=',today_date),('week_ending_date','>=',today_date)])
		for current_week in current_week_records:
			previous_week_ending_date = current_week.week_starting_date - timedelta(days=1)
			previous_week = self.env['store.scheduling'].search([('week_ending_date','=',previous_week_ending_date),('store_id','=',current_week.store_id.id)],limit=1)
			if previous_week:
				previous_to_previous_week_ending_date = previous_week.week_starting_date - timedelta(days=1)
				previous_to_previous_week = self.env['store.scheduling'].search([('week_ending_date','=',previous_to_previous_week_ending_date),('store_id','=',previous_week.store_id.id)],limit=1)
				scheduling_records = self.env['store.scheduling'].search([('week_ending_date','<',previous_to_previous_week.week_starting_date),('store_id','=',previous_to_previous_week.store_id.id)])
				for scheduler in scheduling_records:
					if scheduler:
						scheduler.is_readonly_record = True
						# scheduler.state = 'done'
