# -*- coding: utf-8 -*-
from odoo import api, models, fields,_
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import ValidationError, AccessError, UserError
from lxml import etree
import json
import simplejson


class StoreScheduling(models.Model):
    _name = "store.scheduling"
    _description = "Store Scheduling"
    _rec_name = 'combination_rec_name'
    _order = "week_starting_date desc"
    _inherit = ["mail.thread","mail.activity.mixin"]

###########################STORE FIELDS DONE SECTION###############################################################################


    # Scheduling Main Fields
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        domain="[('id', 'in', parent.store_employees_ids)]"
    )
    store_id = fields.Many2one('store.store', string="Store",tracking=True, required=True)
    store_number = fields.Integer(string="Store No.",related="store_id.store_number") 
    week_starting_date = fields.Date(string="Week Starting Date",tracking=True,copy=False, required=True)
    week_ending_date = fields.Date(string="Week Ending Date",tracking=True,copy=False, required=True)
    combination_rec_name = fields.Char(string="Week No",compute="_compute_combination_rec_name",store=True,copy=False)
    currency_id = fields.Many2one('res.currency', string="Currency",default=lambda self: self.env.user.company_id.currency_id,readonly=True,tracking=True)
    geo_location_id = fields.Many2one('emp.geo_location', string="Geo Location",related="store_id.geo_location_id")

    # RM- AUG21-2025 Cash Deposit Remider
    @api.model
    def _check_cash_deposit_alert(self):
        current_date = fields.Date.today()
        current_day = current_date.strftime("%A").lower()
        domain = [(current_day, '=', True)]
        scheduling_ids = self.env['store.scheduling'].search([('week_starting_date','<=',current_date),('week_ending_date','>=',current_date)])
        for sch in scheduling_ids:
            recipients = sch.store_id.sudo().recipient_user_ids
            recipient_emails = []
            for user in recipients:
                email = (user.email_id or user.email or "").strip()
                if email and "\n" not in email and "\r" not in email:
                    recipient_emails.append(email)

            deposit_found = False
            if sch.store_cash_deposit_ids:
                for dep_line in sch.store_cash_deposit_ids:
                    if dep_line.selected_date == current_date:
                        deposit_found = True
            if deposit_found is False:
                if sch.store_id[current_day] == True:
                    template = self.env.ref('bsi_subway_base.bsi_email_template_cash_deposit_alert')
                    ctx = {
                        'current_date': current_date.strftime("%d-%m-%Y"),
                        'current_day': current_day,
                        'company_id' : self.env.company.name,
                        'store_name' : sch.store_id.name
                    }
                    subject = (template.subject or "").replace("\n", " ").replace("\r", " ")
                    template.with_context(ctx).send_mail(
                        sch.store_id.id,
                        force_send=True,
                        email_values={
                            'email_to':  ",".join(recipient_emails),
                            'subject': subject,
                        }
                    )

        # stores = self.env['store.store'].search(domain)
        # for store in stores:
        #     recipient_users = store.recipient_user_ids

        #     recipient_emails = []
        #     for user in recipient_users:
        #         email = (user.email_id or user.email or "").strip()
        #         if email and "\n" not in email and "\r" not in email:
        #             recipient_emails.append(email)

        #     if recipient_emails:
        #         template = self.env.ref('bsi_subway_base.bsi_email_template_cash_deposit_alert')
        #         ctx = {
        #             'current_date': current_date.strftime("%d-%m-%Y"),
        #             'current_day': current_day,
        #         }

        #         subject = (template.subject or "").replace("\n", " ").replace("\r", " ")
        #         template.with_context(ctx).send_mail(
        #             store.id,
        #             force_send=True,
        #             email_values={
        #                 'email_to': ",".join(recipient_emails),
        #                 'subject': subject,
        #             }
        #         )

    # GS- FEB19 NEW METHOD WITH CORRECT WEEK COUNT
    @api.depends('week_starting_date', 'week_ending_date')
    def _compute_combination_rec_name(self):
        for rec in self:
            combination_rec_name = ''
            if rec.week_ending_date:
                # Adjust week_ending_date to the previous Wednesday if it isn't already Wednesday
                weekday = rec.week_ending_date.weekday()  # 0 is Monday, 1 is Tuesday, ..., 6 is Sunday
                if weekday < 2:  # If it's Monday or Tuesday
                    adjusted_week_end = rec.week_ending_date - timedelta(days=weekday + 3)  # Go back to previous Wednesday
                else:  # If it's Wednesday or later
                    adjusted_week_end = rec.week_ending_date - timedelta(days=weekday - 2)  # Go back to current Wednesday
                # Calculate the week number based on the adjusted week end
                week_num = adjusted_week_end.isocalendar()[1]
                # Get the ISO year (this is the correct year based on the week number)
                iso_year = adjusted_week_end.isocalendar()[0]
                combination_rec_name = 'W' + str(week_num) + " " + str(iso_year)
            rec.combination_rec_name = combination_rec_name

    @api.constrains('combination_rec_name')
    def constrains_week_number(self):
        for rec in self:
            same_week_num = self.env['store.scheduling'].search([('week_starting_date','=',rec.week_starting_date),('week_ending_date','=',rec.week_ending_date),('store_id','=',rec.store_id.id),('id','!=',rec.id)],limit=1)
            if same_week_num:
                raise ValidationError("You cannot create Same Week for Particular Store. Store: {0}, Week: {1}".format(rec.store_id.name, rec.combination_rec_name))

###########################SALES DONE SECTION################################################################################################


    #Sales Data Fields
    last_week_sale = fields.Float(string="Last Week's Sales", compute="_compute_last_week_sale",store=True,tracking=True, help="Compute Field - Fetches and sets the previous week’s net sales for the same store")#Compute
    last_year_this_week_sale = fields.Float(string="Last Year's this week Sales", compute="_compute_last_year_this_week_sale", store=True,tracking=True, help="Compute Field - Calculates the corresponding Wednesday–Tuesday week from last year and updates the net sales for the same store")#Compute
    net_sales = fields.Float(string="Net Sales",tracking=True,copy=False, help="Input Field = data comes from LIVE IQ Api(Sale summary API).")
    ytd_avg_net_sales = fields.Float('YTD Avg. Sales', compute="_compute_ytd_avg_net_sales", tracking=True, store=True, help="Compute Field - Calculates the store’s YTD average net sales using data from the first Wednesday of the year up to the current week")

    @api.depends('week_starting_date')
    def _compute_last_week_sale(self):
        for rec in self:
            last_week_sale = 0.0
            if rec.week_starting_date:
                last_week_ending_date = rec.week_starting_date - timedelta(days=1)
                last_week = self.env['store.scheduling'].search([('week_ending_date','=',last_week_ending_date), ('store_id', '=', rec.store_id.id)], limit=1)
                if last_week and last_week.net_sales:
                    last_week_sale = last_week.net_sales
            rec.last_week_sale = last_week_sale

    # GS- FEB19 NEW METHOD WITH CORRECT WEEK COUNT
    @api.depends('week_starting_date', 'week_ending_date')
    def _compute_last_year_this_week_sale(self):
        for rec in self:
            last_year_this_week_sale = 0.0
            if rec.week_starting_date and rec.week_ending_date:
                weekday = rec.week_ending_date.weekday()  # 0 is Monday, 1 is Tuesday, ..., 6 is Sunday

                if weekday < 2:  # If it's Monday or Tuesday
                    adjusted_week_end = rec.week_ending_date - timedelta(days=weekday + 3)  # Go back to previous Wednesday
                else:  # If it's Wednesday or later
                    adjusted_week_end = rec.week_ending_date - timedelta(days=weekday - 2)  # Go back to current Wednesday

                # Calculate the week number based on the adjusted week end
                week_num = adjusted_week_end.isocalendar()[1]
                iso_year = adjusted_week_end.isocalendar()[0]
                last_year_week_num = 'W' + str(week_num) + " " + str(iso_year-1)
                last_year_this_week = self.env['store.scheduling'].search([('combination_rec_name','=',last_year_week_num),('store_id','=',rec.store_id.id)],limit=1)
                if last_year_this_week and last_year_this_week.net_sales:
                        last_year_this_week_sale = last_year_this_week.net_sales
            rec.last_year_this_week_sale = last_year_this_week_sale


    @api.depends('week_ending_date', 'net_sales')
    def _compute_ytd_avg_net_sales(self):
        for rec in self:
            ytd_avg_net_sales = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)


                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])

                total_sales = sum(record.net_sales for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_avg_net_sales = total_sales / total_weeks
                else:
                    ytd_avg_net_sales = rec.net_sales  # Handle case where there are no records

            rec.ytd_avg_net_sales = ytd_avg_net_sales

#################################Backend Purpose DONE##############################################################################



    # Fields for Backend Purpose
    active = fields.Boolean(string="Active",default=True)
    is_user_admin = fields.Boolean(string="Is user Admin",compute="_compute_is_user_admin")
    current_user_id = fields.Many2one('res.users', string="Current User", default=lambda self: self.env.user, readonly=True)
    is_readonly_record = fields.Boolean(string="Is Readonly Record")
    state = fields.Selection(selection=[('draft','Draft'),('to_be_approve','To be Approve'),('approved','Approved'),('rejected','Rejected'),('active','Active'),('cancelled','Cancelled'),('done','Done')], string='Status',default='draft',tracking=True)

    @api.depends('current_user_id')
    def _compute_is_user_admin(self):
        for rec in self:
            user_id = self.env.user
            # if user_id.has_group('base.group_erp_manager'):
            # GS FEB19-- Chnaged Access Rights from New Access to Find Owner and Admin
            if user_id.has_group('bsi_subway_base.store_owner') or user_id.has_group('bsi_subway_base.store_admin'):
                rec.is_user_admin = True
            else:
                rec.is_user_admin = False

    @api.model
    def fields_view_get(self,view_id=None, view_type='form',toolbar=False,submenu=False):
        res = super(StoreScheduling, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                if 'readonly' not in modifiers:
                    # modifiers['readonly'] = [['is_readonly_record','=',True],['is_user_admin','=',False]]
                    # GS - Moved code to If state Done it will become readonly for DM & SM. 
                    modifiers['readonly'] = [['state','=', 'done'],['is_user_admin','=',False]]
                else:
                    if type(modifiers['readonly']) != bool:
                        modifiers['readonly'].insert(0, '|')
                        # modifiers['readonly'] += [['is_readonly_record','=',True],['is_user_admin','=',False]]
                        # GS - Moved code to If state Done it will become readonly for DM & SM. 
                        modifiers['readonly'] += [['state','=', 'done'],['is_user_admin','=',False]]
                node.set('modifiers', simplejson.dumps(modifiers))
                res['arch'] = etree.tostring(doc)
        return res

    def action_start(self):
        self.state = 'active'

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_done(self):
        self.state = 'done'

    def action_start_scheduling(self):
        # self.compute_all_related_data()
        if self.total_scheduled_hours and self.max_allow_hr_range and self.min_allow_hr_range:
            if self.total_scheduled_hours < self.max_allow_hr_range or self.total_scheduled_hours > self.min_allow_hr_range:
                self.state = 'to_be_approve'
                store_manager_ids = self.store_id.store_manager_ids
                district_manager_ids = self.store_id.district_manager_ids
                if district_manager_ids:
                    for district_manager_id in district_manager_ids:
                        if district_manager_id and not district_manager_id.user_id:
                            msg = "Assigned manager (%s) don't have user, Kindly create user first." % (district_manager_id.combine_name)
                            raise UserError(msg)
                        # Create a mail.activity record
                        today = datetime.today()
                        tomorrow = today + timedelta(days=1)
                        activity_id = self.env['mail.activity'].create({
                            'res_model': 'store.scheduling',
                            'res_model_id': self.env.ref('bsi_subway_base.model_store_scheduling').id,
                            'res_id': self.id,
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,  # Change as needed
                            'summary': 'Store Scheduling Request For: ' + str(self.store_id.name)+ ' ' +self.display_name,
                            'note': 'Scheduling Review Request is created For: '  + str(self.store_id.name)+ ' ' + str(self.display_name) + " by: "+ str(self.env.user.name),
                            'user_id': district_manager_id.user_id.id,  # Assign to the current user
                            'date_deadline': tomorrow,
                        })
            else:
                self.state = 'approved'


######################################################################################################################################


    # Store Planning Tab
    allowed_scheduling_hours = fields.Float(string="Allowed Scheduling Hours",compute="_compute_allowed_scheduling_hours",store=True,tracking=True)
    total_scheduled_hours = fields.Float(string="Total Scheduled Hours", compute="compute_total_scheduled_hours", store=True,tracking=True)
    over_or_short_allowed_hours = fields.Float(string="Over/Short Allowed Hours",compute="_compute_over_or_short_allowed_hours", store=True,tracking=True,
            help="Formula: Total Scheduled Hours - Allowed Scheduling Hours")

    # Store Working Tab
    total_worked_hours = fields.Float(string="Total Worked Hours", compute="compute_total_worked_hours", store=True,tracking=True,
        help=" Formula : Total of working tab")

    #Scheduling and Work Hours
    over_or_short_worked_hours = fields.Float(string="Over/Short Worked Hours",compute="_compute_over_or_short_worked_hours", store=True,tracking=True,
            help="Total Worked Hours - Total Scheduled Hours")

    # For buttons in header
    is_allowed_hours_match = fields.Boolean(string="Is Allowed Hours Match")


    #NEED TO CHECK
    @api.depends('week_starting_date')
    def _compute_allowed_scheduling_hours(self):
        for rec in self:
            scheduling_hours = 0.0
            # if rec.ytd_avg_net_sales:
            #     store_allowed_hours = self.env['store.actual.hours'].search([('week_actual_sale','>=',rec.ytd_avg_net_sales)],order='week_actual_sale asc',limit=1)   
            #     if store_allowed_hours and store_allowed_hours.week_actual_sale and store_allowed_hours.week_actual_hours:
            #         scheduling_hours = (rec.ytd_avg_net_sales * store_allowed_hours.week_actual_hours)/store_allowed_hours.week_actual_sale
            # rec.allowed_scheduling_hours = scheduling_hours
            if rec.week_starting_date:
                last_week_ending_date = rec.week_starting_date - timedelta(days=1)
                last_week = self.env['store.scheduling'].search([('week_ending_date','=',last_week_ending_date), ('store_id', '=', rec.store_id.id)], limit=1)
                if last_week and last_week.last_week_sale:
                    last_to_last_week_sale = last_week.last_week_sale
                    store_allowed_hours = self.env['store.actual.hours'].search([('week_actual_sale','>=',last_to_last_week_sale)],order='week_actual_sale asc',limit=1)
                    if store_allowed_hours and store_allowed_hours.week_actual_sale and store_allowed_hours.week_actual_hours:
                        scheduling_hours = (last_to_last_week_sale * store_allowed_hours.week_actual_hours)/store_allowed_hours.week_actual_sale
            rec.allowed_scheduling_hours = scheduling_hours

    @api.depends("bsi_work_planning_ids.total_scheduled_hours_week")
    def compute_total_scheduled_hours(self):
        for rec in self:
            temp_total_hours = 0.0
            if rec.bsi_work_planning_ids:
                for record in rec.bsi_work_planning_ids:
                    if record.total_scheduled_hours_week:
                        temp_total_hours += record.total_scheduled_hours_week
            rec.total_scheduled_hours = temp_total_hours

    @api.depends('allowed_scheduling_hours','total_scheduled_hours')
    def _compute_over_or_short_allowed_hours(self):
        for rec in self:
            over_or_short_allowed_hours = 0.0
            if rec.allowed_scheduling_hours and rec.total_scheduled_hours:
                over_or_short_allowed_hours = rec.total_scheduled_hours - rec.allowed_scheduling_hours
            rec.over_or_short_allowed_hours = over_or_short_allowed_hours

    @api.depends("bsi_store_work_ids.total_worked_hours_week")
    def compute_total_worked_hours(self):
        for rec in self:
            temp_total_hours = 0.0
            if rec.bsi_store_work_ids :
                for record in rec.bsi_store_work_ids:
                    if record.total_worked_hours_week:
                        temp_total_hours += record.total_worked_hours_week
            rec.total_worked_hours = temp_total_hours

    @api.depends('total_worked_hours','total_scheduled_hours')
    def _compute_over_or_short_worked_hours(self):
        for rec in self:
            over_or_short_worked_hours = 0.0
            if rec.total_worked_hours and rec.total_scheduled_hours:
                over_or_short_worked_hours = rec.total_worked_hours - rec.total_scheduled_hours
            rec.over_or_short_worked_hours = over_or_short_worked_hours


    @api.onchange('allowed_scheduling_hours','total_scheduled_hours')
    def onchange_is_allowed_hours_match(self):
        for rec in self:
            check_slot_hrs = False
            if rec.allowed_scheduling_hours and rec.total_scheduled_hours:
                if rec.allowed_scheduling_hours == rec.total_scheduled_hours:
                    check_slot_hrs = True
                else :
                    check_slot_hrs = False
            rec.is_allowed_hours_match = check_slot_hrs

######################################################################################################################################

    # Food Fields
    allowed_percentage_food_cost = fields.Float(string="Allowed Food Cost (%)", default="27.0", tracking=True, help="Input Field (Default value set from code)", group_operator="avg")#INPUT
    allowed_food_cost = fields.Float(string="Allowed Food Cost", compute="_compute_allowed_food_cost",store=True,tracking=True,
        help="Formula: Current Year's total week's sales average * (Allowed (%) Food Cost / 100)")

    food_cost = fields.Float(string="FC", tracking=True, help="""Food Cost 
    Value fetched from sheet or bank transaction""")#INPUT
    manual_food_cost = fields.Float(string="M FC", tracking=True, help="""Manual Food Cost
    This value is entered by the store manager or district manager""")#INPUT
    total_food_cost = fields.Float(string="TFC", tracking=True, compute="_compute_total_food_cost", help="""Total Food Cost
        Formula : TFC = FC+ M FC""", store=True)
    food_cost_in_percentage = fields.Float(string="Food Cost %", compute="compute_food_cost_in_percentage",store=True,tracking=True,
            help="Formula: (TFC / Net Sales) * 100")

    over_or_short_food_cost = fields.Float(string="Over/Short Food Cost",compute="_compute_over_or_short_food_cost", store=True,tracking=True,
            help="Formula: TFC - Allowed Food Cost")

    ytd_average_food_cost = fields.Float(string="YTD Average Food Cost", compute="_compute_ytd_average_food_cost", store=True, tracking=True, help="Compute Field - Calculates the store’s YTD average food cost using data from the first Wednesday of the year up to the current week.")#MADE GS
    ytd_average_food_cost_percentage = fields.Float(string="YTD Avg Food Cost (%)",compute="_compute_ytd_average_food_cost_percentage",store=True,tracking=True, help="Compute Field - Calculates the store’s YTD average food cost percentage using data from the first Wednesday of the year up to the current week.")#MADE GS
    ytd_over_or_short_food_cost = fields.Float(string="YTD Over/Short Food Cost", compute="_compute_ytd_over_or_short_food_cost" , tracking=True, store=True, help="Compute Field - Calculates the store’s YTD total over-or-short food cost using data from the first Wednesday of the year up to the current week.")

    #RM - [28/07/2025] - String change "Truck Order #1" to "Total Truck Order"
    truck_order_1 = fields.Float(string="Total Truck Order", compute="_compute_total_truck_order_amount", tracking=True,  store=True, help="Formula: sum(Truck Order Amount)")#Compute
    over_or_short_food_bank_and_truck = fields.Float(string="Over/Short Truck & Food Order Bank", compute="_compute_over_or_short_food_bank_and_truck",
     tracking=True, store=True, help="Formula: TFC - Total Truck Order")

    truck_order_ids = fields.One2many(
        'bsi.store.scheduling.truck.line',
        'bsi_scheduling_truck_id',
        string='Truck Order Details'
    )

    @api.depends('truck_order_ids.truck_order_amount')
    def _compute_total_truck_order_amount(self):
        for rec in self:
            rec.truck_order_1 = sum(line.truck_order_amount for line in rec.truck_order_ids)

    @api.depends('food_cost','manual_food_cost')
    def _compute_total_food_cost(self):
        for rec in self:
            rec.total_food_cost = rec.food_cost + rec.manual_food_cost

    @api.depends('allowed_percentage_food_cost','ytd_avg_net_sales')
    def _compute_allowed_food_cost(self):
        for rec in self:
            allowed_food_cost = 0.0
            if  rec.ytd_avg_net_sales and rec.allowed_percentage_food_cost:
                allowed_food_cost = rec.ytd_avg_net_sales * (rec.allowed_percentage_food_cost/100)
            rec.allowed_food_cost = allowed_food_cost

    @api.depends('net_sales', 'total_food_cost')
    def compute_food_cost_in_percentage(self):
        for rec in self:
            percentage = 0.00
            if rec.total_food_cost and rec.net_sales:
                percentage = (rec.total_food_cost * 100) / rec.net_sales
            rec.food_cost_in_percentage = percentage


    @api.depends('total_food_cost','allowed_food_cost')
    def _compute_over_or_short_food_cost(self):
        for rec in self:
            over_or_short_food_cost = 0.0
            if rec.total_food_cost and rec.allowed_food_cost:
                over_or_short_food_cost = rec.total_food_cost - rec.allowed_food_cost
            rec.over_or_short_food_cost = over_or_short_food_cost

    @api.depends('week_ending_date', 'total_food_cost')
    def _compute_ytd_average_food_cost(self):
        for rec in self:
            ytd_average_food_cost = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total_cost = sum(record.total_food_cost for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_average_food_cost = total_cost / total_weeks
                else:
                    ytd_average_food_cost = rec.total_food_cost  # Handle case where there are no records

            rec.ytd_average_food_cost = ytd_average_food_cost

    @api.depends('week_ending_date', 'food_cost_in_percentage')
    def _compute_ytd_average_food_cost_percentage(self):
        for rec in self:
            ytd_average_food_cost_percentage = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)


                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                # Calculate the average of food_cost_in_percentage for these records
                total_expense = sum(record.food_cost_in_percentage for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_average_food_cost_percentage = total_expense / total_weeks
                else:
                    ytd_average_food_cost_percentage = rec.food_cost_in_percentage  # Handle case where there are no records

            rec.ytd_average_food_cost_percentage = ytd_average_food_cost_percentage


    @api.depends('over_or_short_food_cost', 'week_ending_date')
    def _compute_ytd_over_or_short_food_cost(self):
        for rec in self:
            ytd_over_or_short_food_cost = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total = sum(record.over_or_short_food_cost for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_over_or_short_food_cost = total
                else:
                    ytd_over_or_short_food_cost = rec.over_or_short_food_cost  # Handle case where there are no records

            rec.ytd_over_or_short_food_cost = ytd_over_or_short_food_cost


    @api.depends('total_food_cost', 'truck_order_1')
    def _compute_over_or_short_food_bank_and_truck(self):
        for rec in self:
            over_or_short_food_bank_and_truck = 0
            if rec.total_food_cost and rec.truck_order_1:
                over_or_short_food_bank_and_truck = rec.total_food_cost - rec.truck_order_1
            rec.over_or_short_food_bank_and_truck = over_or_short_food_bank_and_truck


###############################PAYROll#######################################################################################################

    # PAYROLL FIELDS
    payroll_taxes = fields.Float(string="Employer Taxes",tracking=True, help="Value fetched from sheet or bank transaction")#INPUT CURRENTLY
    payroll_productivity = fields.Float(string="M Payroll", tracking=True, help="""Manual Payroll 
    Input Field = data comes from LIVE IQ Api(Sale summary API) ==> Controlsheet API.""")#INPUT + Controlsheet API
    paychex_total_debit = fields.Float(string="Total Debit/Gross Payroll", tracking=True, help="Input Field = data comes from LIVE IQ Api(Sale summary API) ==> Controlsheet API.")#INPUT + Controlsheet API
    payroll_total = fields.Float(string="Payroll Total", compute='_compute_total_payroll', store=True, tracking=True, help="Formula :  M Payroll + Total Debit/Gross Payroll")#Compute
    percentage_of_payroll = fields.Float(string="(%) of Payroll", compute="_compute_percentage_of_payroll", tracking=True, store=True,
        help="Formula :  (Total Debit/Gross Payroll / Net Sales) * 100")#Compute
    ytd_average_percentage_of_payroll = fields.Float(string="YTD Avg (%) of Payroll", compute="_compute_ytd_average_percentage_of_payroll", tracking=True, store=True, help="Compute Field - Calculates the store’s YTD average payroll percentage using data from the first Wednesday of the year up to the current week.")#Compute


    fc_and_lc_percentage = fields.Float(string="FC & LC (%)", compute="_compute_fc_and_lc_percentage", tracking=True, store=True,
        help="Formula :  Food Cost % + (%) of Payroll")#Compute
    ytd_fc_and_lc_percentage = fields.Float(string="YTD FC & LC (%)", compute="_compute_ytd_fc_and_lc_percentage", tracking=True, store=True, help="Compute Field - Calculates the store’s YTD average food and labor cost percentage using data from the first Wednesday of the year up to the current week.")#Compute

    total_hours = fields.Float(string="Total Hours", help="Value fetched from sheet or bank transaction")
    fixed_hours = fields.Float(string="Fixed Hours", help="Value fetched from sheet or bank transaction")

    matrix_allowed_hours = fields.Float(string="Matrix Allowed Hours", help="Value fetched from sheet or bank transaction")
    over_or_short_matrix_hours = fields.Float(string="Over or Short Matrix Hours", compute="_compute_over_or_short_matrix_hours", tracking=True, 
        store=True, help="Formula :  Total Hours(Worked) - Matrix Hours(Scheduled Hours)")
    ytd_over_or_short_in_hours = fields.Float(string="YTD Over/Short in Hours", compute="_compute_ytd_over_or_short_in_hours", tracking=True, 
        store=True, help="Compute Field - Calculates the store’s YTD total over-or-short matrix hours using data from the first Wednesday of the year up to the current week.")#Compute
    ytd_over_or_short_dollar_in_lc = fields.Float(string="YTD Over/Short $ in LC", compute="_compute_ytd_over_or_short_dollar_in_lc", tracking=True, 
        store=True, help="Formula : YTD Over/Short in Hours*Average Hourly Pay")
    ytd_over_or_short_dollar_in_fc_and_lc = fields.Float(string="YTD Over/Short $ in FC and LC", compute="_compute_ytd_over_or_short_dollar_in_fc_and_lc", tracking=True, 
        store=True, help="Formula : YTD Over/Short $ in LC + YTD Over/Short Food Cost")#Compute
    
    ytd_total_hours = fields.Float(string="YTD Total Hours", compute="_compute_ytd_total_hours", tracking=True, 
        store=True, help="Compute Field - Calculates the store’s YTD total hours using data from the first Wednesday of the year up to the current week")#Compute

    per_hours_gain_or_loss = fields.Float(string="Per Hours Gain or Loss", compute="_compute_per_hours_gain_or_loss", tracking=True, 
        store=True, help="Formula : YTD Over/Short $ in FC and LC / YTD Total Hours")

    average_hourly_pay = fields.Float(string="Average Hourly Pay", compute="_compute_average_hourly_pay", tracking=True, store=True,
        help="Formula :  Total Debit/Gross Payroll / Total Hours(Worked Hours)")#Compute
    ytd_average_hourly_pay = fields.Float(string="YTD Average Hourly Pay", compute="_compute_ytd_average_hourly_pay", tracking=True, store=True, help="Compute Field - Calculates the store’s YTD average hourly pay using data from the first Wednesday of the year up to the current week.")#Compute

    total_tips = fields.Float(string="Total Tips", help="Input Field - data comes from LIVE IQ Api")#INPUT
    tips_per_employee_hour = fields.Float(string="Tips Per Employee Hour", compute="_compute_tips_per_employee_hour", tracking=True, 
        store=True, help="Formula : Total Tips / Total Hours(Worked Hours)")#Compute
    total_hourly_pay_including_tips = fields.Float(string="Total Hourly Pay Including Tips", compute="_compute_total_hourly_pay_including_tips", 
        tracking=True, store=True, help="Formula : Average Hourly Pay + Tips Per Employee Hour")#Compute

    @api.depends('payroll_productivity', 'paychex_total_debit')
    def _compute_total_payroll(self):
        for record in self:
            record.payroll_total = record.payroll_productivity + record.paychex_total_debit

    @api.depends('total_hours', 'total_worked_hours', 'matrix_allowed_hours', 'total_scheduled_hours')
    def _compute_over_or_short_matrix_hours(self):
        for rec in self:
            over_or_short_matrix_hours = 0.00
            if rec.total_hours or rec.matrix_allowed_hours:
                over_or_short_matrix_hours = rec.total_hours - rec.matrix_allowed_hours

            elif rec.total_worked_hours or rec.matrix_allowed_hours:
                over_or_short_matrix_hours = rec.total_worked_hours - rec.matrix_allowed_hours
            
            elif rec.total_hours or rec.total_scheduled_hours:
                over_or_short_matrix_hours = rec.total_hours - rec.total_scheduled_hours

            elif rec.total_worked_hours or rec.total_scheduled_hours:
                over_or_short_matrix_hours = rec.total_worked_hours - rec.total_scheduled_hours

            rec.over_or_short_matrix_hours = over_or_short_matrix_hours

    @api.depends('over_or_short_matrix_hours', 'week_ending_date')
    def _compute_ytd_over_or_short_in_hours(self):
        for rec in self:
            ytd_over_or_short_in_hours = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total = sum(record.over_or_short_matrix_hours for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_over_or_short_in_hours = total
                else:
                    ytd_over_or_short_in_hours = rec.over_or_short_matrix_hours  # Handle case where there are no records

            rec.ytd_over_or_short_in_hours = ytd_over_or_short_in_hours


    @api.depends('ytd_over_or_short_in_hours', 'average_hourly_pay')
    def _compute_ytd_over_or_short_dollar_in_lc(self):
        for rec in self:
            ytd_over_or_short_dollar_in_lc = rec.ytd_over_or_short_in_hours * rec.average_hourly_pay
            rec.ytd_over_or_short_dollar_in_lc = ytd_over_or_short_dollar_in_lc

    @api.depends('ytd_over_or_short_dollar_in_lc', 'ytd_over_or_short_food_cost')
    def _compute_ytd_over_or_short_dollar_in_fc_and_lc(self):
        for rec in self:
            ytd_over_or_short_dollar_in_fc_and_lc = 0
            if rec.ytd_over_or_short_dollar_in_lc and rec.ytd_over_or_short_food_cost:
                ytd_over_or_short_dollar_in_fc_and_lc = rec.ytd_over_or_short_dollar_in_lc + rec.ytd_over_or_short_food_cost
            rec.ytd_over_or_short_dollar_in_fc_and_lc = ytd_over_or_short_dollar_in_fc_and_lc

    @api.depends('total_hours', 'total_worked_hours', 'week_ending_date')
    def _compute_ytd_total_hours(self):
        for rec in self:
            ytd_total_hours = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                # total = sum(record.total_hours for record in scheduling_records)
                total = sum(record.total_hours if record.total_hours else record.total_worked_hours for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_total_hours = total
                else:
                    ytd_total_hours = rec.total_hours  # Handle case where there are no records

            rec.ytd_total_hours = ytd_total_hours


    @api.depends('ytd_over_or_short_dollar_in_fc_and_lc', 'ytd_total_hours')
    def _compute_per_hours_gain_or_loss(self):
        for rec in self:
            per_hours_gain_or_loss = 0.00
            if rec.ytd_over_or_short_dollar_in_fc_and_lc and rec.ytd_total_hours:
                per_hours_gain_or_loss = rec.ytd_over_or_short_dollar_in_fc_and_lc / rec.ytd_total_hours
            rec.per_hours_gain_or_loss = per_hours_gain_or_loss



    @api.depends('paychex_total_debit', 'net_sales')
    def _compute_percentage_of_payroll(self):
        for rec in self:
            percentage_of_payroll = 0.00
            if rec.paychex_total_debit and rec.net_sales:
                percentage_of_payroll = (rec.paychex_total_debit / rec.net_sales) * 100
            rec.percentage_of_payroll = round(percentage_of_payroll, 2)

    @api.depends('percentage_of_payroll', 'week_ending_date', 'week_starting_date')
    def _compute_ytd_average_percentage_of_payroll(self):
        for rec in self:
            ytd_average_percentage_of_payroll = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total = sum(record.percentage_of_payroll for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_average_percentage_of_payroll = total / total_weeks
                else:
                    ytd_average_percentage_of_payroll = rec.percentage_of_payroll  # Handle case where there are no records

            rec.ytd_average_percentage_of_payroll = ytd_average_percentage_of_payroll


    @api.depends('food_cost_in_percentage', 'percentage_of_payroll')
    def _compute_fc_and_lc_percentage(self):
        for rec in self:
            fc_and_lc_percentage = 0.00
            if rec.food_cost_in_percentage or rec.percentage_of_payroll:
                fc_and_lc_percentage = rec.food_cost_in_percentage + rec.percentage_of_payroll
            rec.fc_and_lc_percentage = fc_and_lc_percentage


    @api.depends('week_ending_date', 'fc_and_lc_percentage')
    def _compute_ytd_fc_and_lc_percentage(self):
        for rec in self:
            ytd_fc_and_lc_percentage = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total = sum(record.fc_and_lc_percentage for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_fc_and_lc_percentage = total / total_weeks
                else:
                    ytd_fc_and_lc_percentage = rec.fc_and_lc_percentage  # Handle case where there are no records

            rec.ytd_fc_and_lc_percentage = ytd_fc_and_lc_percentage


    @api.depends('paychex_total_debit', 'total_hours', 'total_worked_hours')
    def _compute_average_hourly_pay(self):
        for rec in self:
            average_hourly_pay = 0.00
            if rec.total_hours and rec.paychex_total_debit:
                average_hourly_pay = rec.paychex_total_debit / rec.total_hours
            elif rec.total_worked_hours and rec.paychex_total_debit:
                average_hourly_pay = rec.paychex_total_debit / rec.total_worked_hours
            rec.average_hourly_pay = average_hourly_pay

    @api.depends('week_ending_date', 'average_hourly_pay')
    def _compute_ytd_average_hourly_pay(self):
        for rec in self:
            ytd_average_hourly_pay = 0
            if rec.week_ending_date:
                current_year = rec.week_ending_date.year   # Extract current year
                
                # Get the start of the year (January 1st)
                start_of_year = datetime(current_year, 1, 1).date()
                first_wednesday = start_of_year + timedelta(days=(2 - start_of_year.weekday()) % 7)

                # Filter records for the current year (week_ending_date within the current year)
                scheduling_records = self.search([
                    ('week_ending_date', '>=', first_wednesday),  # Filter records starting from the start of the year
                    ('week_ending_date', '<=', rec.week_ending_date),    # Up to the current date
                    ('store_id', '<=', rec.store_id.id),    # Up to the current date
                ])
                
                total = sum(record.average_hourly_pay for record in scheduling_records)
                total_weeks = len(scheduling_records)

                if total_weeks > 0:
                    ytd_average_hourly_pay = total / total_weeks
                else:
                    ytd_average_hourly_pay = rec.average_hourly_pay  # Handle case where there are no records

            rec.ytd_average_hourly_pay = ytd_average_hourly_pay


    @api.depends('total_tips', 'total_hours', 'total_worked_hours')
    def _compute_tips_per_employee_hour(self):
        for rec in self:
            tips_per_employee_hour = 0.00
            if rec.total_tips and rec.total_hours:
                tips_per_employee_hour = rec.total_tips / rec.total_hours
            elif rec.total_tips and rec.total_worked_hours:
                tips_per_employee_hour = rec.total_tips / rec.total_worked_hours
            rec.tips_per_employee_hour = tips_per_employee_hour

    @api.depends('average_hourly_pay','tips_per_employee_hour')
    def _compute_total_hourly_pay_including_tips(self):
        for rec in self:
            total_hourly_pay_including_tips = 0.00
            if rec.average_hourly_pay or rec.tips_per_employee_hour:
                total_hourly_pay_including_tips = rec.average_hourly_pay + rec.tips_per_employee_hour
            rec.total_hourly_pay_including_tips = total_hourly_pay_including_tips



###########################HOURS FIELDS#############################################


    # One2many Fields
    bsi_work_planning_ids = fields.One2many("bsi.store.planning", "bsi_work_planning_id", string="Store Schedule Planning",compute="_compute_bsi_work_planning_ids",readonly=False,store=True,tracking=True)
    bsi_store_work_ids = fields.One2many("bsi.store.working", "store_scheduling_id", string="Store Schedule Working",compute="_compute_bsi_store_work_ids",store=True,tracking=True)
    store_cash_deposit_ids = fields.One2many('store.cash.deposit', 'store_scheduling_id', string="Store Cash Deposit")


    # For One2many DOMAIN
    store_employees_ids = fields.Many2many('hr.employee', 'rel_employee_scheduling', 'scheduling_id', 'employee_id', string="Employees", related="store_id.employee_ids")
    store_manager_ids = fields.Many2many('hr.employee', 'rel_store_manager_scheduling', 'scheduling_id', 'employee_id', string="Store Managers", related="store_id.store_manager_ids")
    district_manager_ids = fields.Many2many('hr.employee', 'rel_district_manager_scheduling', 'scheduling_id', 'employee_id', string="District Managers", related="store_id.district_manager_ids")


    grace = fields.Float(string="Grace", tracking=True, help="Input Field")
    min_allow_hr_range = fields.Float(string="Min Allowed Hours Range", compute="_compute_min_allow_hr_range", store=True, tracking=True, help="Formula : Allowed Scheduling Hours - ((Grace*Allowed Scheduling Hours)/100)")

    @api.depends('allowed_scheduling_hours','grace')
    def _compute_min_allow_hr_range(self):
        for rec in self:
            min_allow_hr_range = 0.0
            if rec.allowed_scheduling_hours :
                if rec.grace:
                    min_allow_hr_range = rec.allowed_scheduling_hours - ((rec.grace*rec.allowed_scheduling_hours)/100)
                else :
                    min_allow_hr_range = rec.allowed_scheduling_hours
            rec.min_allow_hr_range = min_allow_hr_range


    max_allow_hr_range = fields.Float(string="Max Allowed Hours Range", compute="_compute_max_allow_hr_range", store=True, tracking=True, help="Formula : Allowed Scheduling Hours - ((Grace*Allowed Scheduling Hours)/100)")    

    @api.depends('allowed_scheduling_hours','grace')
    def _compute_max_allow_hr_range(self):
        for rec in self:
            max_allow_hr_range = 0.0
            if rec.allowed_scheduling_hours :
                if rec.grace:
                    max_allow_hr_range = rec.allowed_scheduling_hours + ((rec.grace*rec.allowed_scheduling_hours)/100)
                else :
                    max_allow_hr_range = rec.allowed_scheduling_hours
            rec.max_allow_hr_range = max_allow_hr_range

    paid_outs  =  fields.Float(string="Paid Outs")

    def get_work_planning_and_store_work_lines(self):
        for rec in self:
            lines = [(5,0,0)]
            today_date = datetime.now().date()
            if rec.store_id:
                store_total_employees_temp = []
                if rec.store_id.employee_ids:
                    store_total_employees_temp.append(rec.store_id.employee_ids.ids)
                if rec.store_id.store_manager_ids:
                    store_total_employees_temp.append(rec.store_id.store_manager_ids.ids)
                if rec.store_id.district_manager_ids:
                    store_total_employees_temp.append(rec.store_id.district_manager_ids.ids)
                if store_total_employees_temp:
                    store_total_employees = list(set(sum(store_total_employees_temp, [])))
                    for store_emp_id in store_total_employees:
                        vals = {'employee_id': store_emp_id}
                        lines.append((0,0,vals))
        return lines

    @api.depends('store_id','week_starting_date','week_ending_date')
    def _compute_bsi_work_planning_ids(self):
        for rec in self:
            rec.bsi_work_planning_ids = rec.get_work_planning_and_store_work_lines()
            rec.action_create_line_data()

    @api.depends('store_id','week_starting_date','week_ending_date')
    def _compute_bsi_store_work_ids(self):
        for rec in self:
            rec.bsi_store_work_ids = rec.get_work_planning_and_store_work_lines()

    # RD - 18 APR
    def view_store_scheduling_record(self):
        action = self.env['ir.actions.actions']._for_xml_id("bsi_subway_base.action_bsi_store_scheduling_views")
        form_view = [(self.env.ref('bsi_subway_base.bsi_store_scheduling_form_view').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.id
        return action

    # Onchange for Sale Data Entry
    @api.constrains('net_sales')
    def compute_all_related_data(self):
        for rec in self:
            if rec.week_ending_date:
                today_date = datetime.now().date()
                startig_date_of_next_week = rec.week_ending_date + timedelta(days=1)
                records_till_current_date = self.env['store.scheduling'].search([('store_id','=',rec.store_id.id),('week_starting_date','>=', startig_date_of_next_week)])
                for record in records_till_current_date:
                    # if record.week_starting_date >= ending_date and record.week_starting_date <= today_date :
                    if record:
                        record._compute_last_week_sale()
                        record._compute_last_year_this_week_sale()
                        record._compute_ytd_avg_net_sales()
                        record._compute_allowed_scheduling_hours()

    def action_create_line_data(self):
        for rec in self:
            if rec.week_starting_date:
                previous_week_ending_date = rec.week_starting_date - timedelta(days=1)
                previous_week = self.env['store.scheduling'].search([('week_ending_date','=',previous_week_ending_date),('store_id','=',rec.store_id.id)], limit=1)
                previous_week_line = False
                for record in rec.bsi_work_planning_ids:
                    is_employee_found = False
                    for line in previous_week.bsi_work_planning_ids:
                        if line.employee_id.id == record.employee_id.id:
                            is_employee_found = True
                            previous_week_line = line

                    if is_employee_found is True:
                        if previous_week_line:
                            record.wed_in = previous_week_line.wed_in
                            record.wed_out = previous_week_line.wed_out
                            record.thur_in = previous_week_line.thur_in
                            record.thur_out = previous_week_line.thur_out
                            record.fri_in = previous_week_line.fri_in
                            record.fri_out = previous_week_line.fri_out
                            record.sat_in = previous_week_line.sat_in
                            record.sat_out = previous_week_line.sat_out
                            record.sun_in = previous_week_line.sun_in
                            record.sun_out = previous_week_line.sun_out
                            record.mon_in = previous_week_line.mon_in
                            record.mon_out = previous_week_line.mon_out
                            record.tue_in = previous_week_line.tue_in
                            record.tue_out = previous_week_line.tue_out

class StoreCashDeposit(models.Model):
    _name = "store.cash.deposit"
    _description = "Store Cash Deposit"

    # RD - Jun 3 New model and fields
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    deposit_amount = fields.Float(string="Deposit Amount")
    image = fields.Binary(string="Image")
    state = fields.Selection([('draft','Draft'),('approved','Approved')],string="State", default='draft')
    store_scheduling_id = fields.Many2one('store.scheduling',string="Store Scheduling")

    # creation_date = fields.Date(
    #     string="Record Creation Date",
    #     default=fields.Date.today,
    #     readonly=True
    # )
    selected_date = fields.Date(string="Selected Deposit Date")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(StoreCashDeposit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form' and self.env.user.has_group('bsi_subway_base.store_manager'):  
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='state']"):
                node.set('readonly', '1')
                modifiers = node.get("modifiers")
                if modifiers:
                    # merge with existing modifiers
                    import json
                    modif = json.loads(modifiers)
                    modif["readonly"] = True
                    node.set("modifiers", json.dumps(modif))
                else:
                    node.set("modifiers", '{"readonly": true}')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.constrains("selected_date", "store_scheduling_id")
    def _check_selected_date_within_week(self):
        for rec in self:
            if rec.store_scheduling_id and rec.selected_date:
                week_start = rec.store_scheduling_id.week_starting_date
                week_end = rec.store_scheduling_id.week_ending_date
                if week_start and week_end:
                    if not (week_start <= rec.selected_date <= week_end):
                        raise ValidationError(_(
                            "Selected date %s is not within the allowed week range %s - %s."
                        ) % (rec.selected_date, week_start, week_end))

    def action_approve_cash_deposit(self):
        self.state = 'approved'

    def action_reset_to_draft(self):
        self.state = 'draft'


class BsiStoreWorking(models.Model):
    _name = "bsi.store.working"
    _description = "Bsi Store Working"

    # RD APR - 10 New model and Fields
    store_scheduling_id = fields.Many2one('store.scheduling', string="Store Scheduling",tracking=True) 
    employee_id = fields.Many2one('hr.employee',string="Employee",tracking=True)
    starting_date = fields.Date(string="Starting Date",related="store_scheduling_id.week_starting_date")
    day_1 = fields.Float(string="Wednesday",tracking=True)
    day_2 = fields.Float(string="Thursday",tracking=True)
    day_3 = fields.Float(string="Friday",tracking=True)
    day_4 = fields.Float(string="Saturday",tracking=True)
    day_5 = fields.Float(string="Sunday",tracking=True)
    day_6 = fields.Float(string="Monday",tracking=True)
    day_7 = fields.Float(string="Tuesday",tracking=True)
    ending_date = fields.Date(string="Ending Date",related="store_scheduling_id.week_ending_date")
    total_worked_hours_week = fields.Float(string="Worked Hours", compute="_compute_total_worked_hours_week", store=True,tracking=True)
    attendance_record_ids = fields.Many2many('hr.attendance',string="Attendance Records")
    emp_per_hr_wage = fields.Float(string="Per Hour Wage",related="employee_id.per_hr_wage")
    total_expenses = fields.Float(string="Total Expenses",compute="_compute_total_expenses", store=True,tracking=True)

    def action_get_attendance(self):
        attendance_ids = self.env['hr.attendance'].search([])

        if self.starting_date and self.ending_date:
            day_2 = self.starting_date + timedelta(days=1)
            day_3 = self.starting_date + timedelta(days=2)
            day_4 = self.starting_date + timedelta(days=3)
            day_5 = self.starting_date + timedelta(days=4)
            day_6 = self.starting_date + timedelta(days=5)

            day_1_worked_hours = 0.0
            day_2_worked_hours = 0.0
            day_3_worked_hours = 0.0
            day_4_worked_hours = 0.0
            day_5_worked_hours = 0.0
            day_6_worked_hours = 0.0
            day_7_worked_hours = 0.0

            for record in attendance_ids:
                if not record.check_in:
                    continue

                check_in_date = record.check_in.date()

                if self.starting_date == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_1_worked_hours += record.worked_hours

                if day_2 == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_2_worked_hours += record.worked_hours

                if day_3 == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_3_worked_hours += record.worked_hours

                if day_4 == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_4_worked_hours += record.worked_hours

                if day_5 == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_5_worked_hours += record.worked_hours

                if day_6 == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_6_worked_hours += record.worked_hours

                if self.ending_date == check_in_date:
                    if self.employee_id.id == record.employee_id.id:
                        day_7_worked_hours += record.worked_hours

            self.day_1 = day_1_worked_hours
            self.day_2 = day_2_worked_hours
            self.day_3 = day_3_worked_hours
            self.day_4 = day_4_worked_hours
            self.day_5 = day_5_worked_hours
            self.day_6 = day_6_worked_hours
            self.day_7 = day_7_worked_hours

    # def action_get_attendance(self):
    #     attendance_ids = self.env['hr.attendance'].search([])
    #     if self.starting_date and self.ending_date:
    #         day_2 = self.starting_date+ timedelta(days=1)
    #         day_3 = self.starting_date+ timedelta(days=2)
    #         day_4 = self.starting_date+ timedelta(days=3)
    #         day_5 = self.starting_date+ timedelta(days=4)
    #         day_6 = self.starting_date+ timedelta(days=5)
    #         day_1_worked_hours = 0.0
    #         day_2_worked_hours = 0.0
    #         day_3_worked_hours = 0.0
    #         day_4_worked_hours = 0.0
    #         day_5_worked_hours = 0.0
    #         day_6_worked_hours = 0.0
    #         day_7_worked_hours = 0.0
    #         for record in attendance_ids:
    #             if self.starting_date == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_1_worked_hours += record.worked_hours

    #             if day_2 == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_2_worked_hours += record.worked_hours

    #             if day_3 == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_3_worked_hours += record.worked_hours

    #             if day_4 == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_4_worked_hours += record.worked_hours

    #             if day_5 == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_5_worked_hours += record.worked_hours

    #             if day_6 == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_6_worked_hours += record.worked_hours

    #             if self.ending_date == datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date():
    #                 if self.employee_id.id == record.employee_id.id:
    #                     day_7_worked_hours += record.worked_hours
            
    #         self.day_1 = day_1_worked_hours
    #         self.day_2 = day_2_worked_hours
    #         self.day_3 = day_3_worked_hours
    #         self.day_4 = day_4_worked_hours
    #         self.day_5 = day_5_worked_hours
    #         self.day_6 = day_6_worked_hours
    #         self.day_7 = day_7_worked_hours

    # RD - APR 17 View Attendance Records
    # def view_attendace_record(self):
    #     attendance_ids = self.env['hr.attendance'].search([])
    #     attendance_record_list = []
    #     if self.starting_date and self.ending_date:
    #         for attendace_record in attendance_ids:
    #             check_in_date = datetime.strptime(str(attendace_record.check_in), "%Y-%m-%d %H:%M:%S").date()
    #             if check_in_date >= self.starting_date and check_in_date <= self.ending_date and self.employee_id.id == attendace_record.employee_id.id:
    #                 attendance_record_list.append((attendace_record.id))
    #     self.attendance_record_ids = attendance_record_list

    #     return self.action_view_hr_attendances_records()

    def view_attendace_record(self):
        attendance_ids = self.env['hr.attendance'].search([])
        attendance_record_list = []

        if self.starting_date and self.ending_date:
            for attendace_record in attendance_ids:
                if attendace_record.check_in:
                    check_in_date = attendace_record.check_in.date()
                    if (
                        check_in_date >= self.starting_date
                        and check_in_date <= self.ending_date
                        and self.employee_id.id == attendace_record.employee_id.id
                    ):
                        attendance_record_list.append(attendace_record.id)

        self.attendance_record_ids = attendance_record_list
        return self.action_view_hr_attendances_records()

    def action_view_hr_attendances_records(self):
        hr_attendaces_records = self.mapped('attendance_record_ids')
        action = self.env['ir.actions.actions']._for_xml_id("hr_attendance.hr_attendance_action")

        if len(hr_attendaces_records) >= 1:
            action['domain'] = [('id', 'in', hr_attendaces_records.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    @api.depends('day_1','day_2','day_3','day_4','day_5','day_6','day_7')
    def _compute_total_worked_hours_week(self):
        for rec in self:
            rec.total_worked_hours_week = rec.day_1 + rec.day_2 +  rec.day_3 +  rec.day_4 + rec.day_5 +  rec.day_6 + rec.day_7

    @api.depends('emp_per_hr_wage','total_worked_hours_week')
    def _compute_total_expenses(self):
        for rec in self:
            total_expenses = 0.0
            if rec.emp_per_hr_wage and rec.total_worked_hours_week:
                total_expenses = rec.emp_per_hr_wage * round(rec.total_worked_hours_week,2)
            rec.total_expenses = total_expenses


class BsiStorePlanningAndScheduling(models.Model):
    _name = "bsi.store.planning"
    _description = "Store Schedule Planning"

    bsi_work_planning_id = fields.Many2one("store.scheduling", string="Store",tracking=True)
    employee_id = fields.Many2one('hr.employee',string="Employee",tracking=True)
    starting_date = fields.Date(string="Starting Date",related="bsi_work_planning_id.week_starting_date",tracking=True)
    day_1 = fields.Many2one("bsi.work.hours", string="Wednesday",tracking=True)
    day_2 = fields.Many2one("bsi.work.hours", string="Thursday",tracking=True)
    day_3 = fields.Many2one("bsi.work.hours", string="Friday",tracking=True)
    day_4 = fields.Many2one("bsi.work.hours", string="Saturday",tracking=True)
    day_5 = fields.Many2one("bsi.work.hours", string="Sunday",tracking=True)
    day_6 = fields.Many2one("bsi.work.hours", string="Monday",tracking=True)
    day_7 = fields.Many2one("bsi.work.hours", string="Tuesday",tracking=True)
    ending_date = fields.Date(string="Ending Date", related="bsi_work_planning_id.week_ending_date")
    total_scheduled_hours_week = fields.Float(string="Scheduled Hours", compute="compute_total_schdelued_hours", store=True,tracking=True)
    selection_planning = fields.Selection(
        [("scheduled", "Scheduled"), ("worked", "Worked")]
    )

    # RD - Apr 9 - New Fields 

    date = fields.Date(string="Date")
    day = fields.Char(string="Day")
    drivein_through = fields.Float(string="Drivein Through")
    open_time = fields.Float(string="Open Time")
    close_time = fields.Float(string="Close Time")
    overlap = fields.Float(string="Overlap")
    prep_time = fields.Float(string="Prep Time")
    store_opening_hours = fields.Float(string="Store Opening Hours")
    store_planeed_hours = fields.Float(string="Store Planned Hours")
    total_employee_actual_hours = fields.Float(string="Total Employees Actual Hours")
    actula_payroll_cost = fields.Float(string="Actual Payroll Cost")

    # RD - 10 May - New Fields

    wed_in = fields.Float(string="Wed - In")
    wed_out = fields.Float(string="Wed - Out")
    thur_in = fields.Float(string="Thu - In")
    thur_out = fields.Float(string="Thu - Out")
    fri_in = fields.Float(string="Fri - In")
    fri_out = fields.Float(string="Fri - Out")
    sat_in = fields.Float(string="Sat - In")
    sat_out = fields.Float(string="Sat - Out")
    sun_in = fields.Float(string="Sun - In")
    sun_out = fields.Float(string="Sun - Out")
    mon_in = fields.Float(string="Mon - In")
    mon_out = fields.Float(string="Mon - Out")
    tue_in = fields.Float(string="Tue - In")
    tue_out = fields.Float(string="Tue - Out")

    @api.onchange('date')
    def onchange_day_date(self):
        for rec in self:
            day = ''
            date = rec.date
            if date:
                day = date.strftime('%A')
            rec.day = day

    @api.constrains('wed_in','wed_out','thur_in','thur_out','fri_in','fri_out','sat_in','sat_out','sun_in','sun_out','mon_in','mon_out','tue_in','tue_out')
    def constrains_week_day_in_out(self):
        for rec in self:
            if rec.wed_in < 0.0 or rec.wed_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Wed in !")

            if rec.wed_out < 0.0 or rec.wed_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Wed Out !")

            if rec.thur_in < 0.0 or rec.thur_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Thur in !")

            if rec.thur_out < 0.0 or rec.thur_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Thur Out !")

            if rec.fri_in < 0.0 or rec.fri_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Fri in !")

            if rec.fri_out < 0.0 or rec.fri_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Fri Out !")

            if rec.sat_in < 0.0 or rec.sat_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Sat in !")

            if rec.sat_out < 0.0 or rec.sat_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Sat Out !")

            if rec.sun_in < 0.0 or rec.sun_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Sun in !")

            if rec.sun_out < 0.0 or rec.sun_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Sun Out !")

            if rec.mon_in < 0.0 or rec.mon_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Mon in !")

            if rec.mon_out < 0.0 or rec.mon_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Mon Out !")

            if rec.tue_in < 0.0 or rec.tue_in > 24.0:
                raise ValidationError("24 hours clock format will be used for Tue in !")

            if rec.tue_out < 0.0 or rec.tue_out > 24.0:
                raise ValidationError("24 hours clock format will be used for Tue Out !")

    @api.depends('wed_in','wed_out','thur_in','thur_out','fri_in','fri_out','sat_in','sat_out','sun_in','sun_out','mon_in','mon_out','tue_in','tue_out')
    def compute_total_schdelued_hours(self):
        for rec in self:
            wed_time = 0.0
            thur_time = 0.0
            fri_time = 0.0
            sat_time = 0.0
            sun_time = 0.0
            mon_time = 0.0
            tue_time = 0.0

            if rec.wed_out and rec.wed_in:
                wed_time = rec.wed_out - rec.wed_in

            if rec.thur_in and rec.thur_out:
                thur_time = rec.thur_out - rec.thur_in

            if rec.fri_in and rec.fri_out:
                fri_time = rec.fri_out - rec.fri_in

            if rec.sat_in and rec.sat_out:
                sat_time = rec.sat_out - rec.sat_in

            if rec.sun_in and rec.sun_out:
                sun_time = rec.sun_out - rec.sun_in

            if rec.mon_in and rec.mon_out:
                mon_time = rec.mon_out - rec.mon_in

            if rec.tue_in and rec.tue_out:
                tue_time = rec.tue_out - rec.tue_in

            rec.total_scheduled_hours_week = wed_time + thur_time + fri_time + sat_time + sun_time + mon_time + tue_time



################# WORK Hours Class - Not used in new code #################
#MP - Query: If not required then let me know, we'll remove this class and related code. Let me know
# for other models too

class BsiWorkHours(models.Model):
    _name = "bsi.work.hours"
    _description = "Bsi Work Hours"
    _rec_name = "name"
    starting_hours = fields.Selection(
        [("0", "0"),("1", "1"),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6"),("7", "7"),
        ("8", "8"),("9", "9"),("10", "10"),("11", "11"),("12", "12"),("13", "13"),("14", "14"),
        ("15", "15"),("16", "16"),("17", "17"),("18", "18"),("19", "19"),("20", "20"),("21", "21"),
        ("22", "22"),("23", "23"),("24", "24"),])
    starting_hour = fields.Float(string="Starting Hours",required=True)
    ending_hours = fields.Selection(
        [("0", "0"),("1", "1"),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6"),("7", "7"),
        ("8", "8"),("9", "9"),("10", "10"),("11", "11"),("12", "12"),("13", "13"),("14", "14"),
        ("15", "15"),("16", "16"),("17", "17"),("18", "18"),("19", "19"),("20", "20"),
        ("21", "21"),("22", "22"),("23", "23"),("24", "24"),])
    ending_hour = fields.Float(string="Ending Hours",required=True)
    worked_hours = fields.Float(string="Worked Hours")
    planned_hours = fields.Float(string="Planned Hours", compute="_compute_planned_hours")
    selection_planning_type = fields.Selection(
        [("scheduled", "Scheduled"), ("worked", "Worked")])
    name = fields.Char(string="Name", compute="_compute_hours", store=True)
    time_type = fields.Selection([('am','AM'),('pm','PM')],string="Time",required=True)
    new_time_type = fields.Selection([('am','AM'),('pm','PM')],string="Time",required=True)
    @api.depends("starting_hour", "ending_hour")
    def _compute_hours(self):
        for rec in self:
            name = ""
            if rec.starting_hour and rec.ending_hour:
                name = str(rec.starting_hour)+' '+ str(rec.time_type) + " - " + str(rec.ending_hour)+' '+str(rec.new_time_type)
            rec.name = name
    @api.depends("starting_hour", "ending_hour")
    def _compute_planned_hours(self):
        for rec in self:
            if rec.starting_hour and rec.ending_hour:
                converted_start_hours = int(rec.starting_hour)
                converted_end_hours = int(rec.ending_hour)
                rec.planned_hours = converted_end_hours - converted_start_hours
            else:
                rec.planned_hours = 0.0
    @api.constrains('ending_hour')
    def constrains_ending_hour(self):
        for rec in self:
            if rec.ending_hour < rec.starting_hour:
                raise ValidationError("Ending Hours cannot be less than Starting Hours")

class BsiStoreSchedulingTruckLine(models.Model):
    _name = 'bsi.store.scheduling.truck.line'
    _description = 'Truck Order Line for Store Scheduling'

    description = fields.Char(string="Description")
    truck_order_amount = fields.Float(string="Truck Order Amount")
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    bsi_scheduling_truck_id = fields.Many2one('store.scheduling', string="Store Scheduling")
