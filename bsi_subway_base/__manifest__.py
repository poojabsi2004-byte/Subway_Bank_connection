# -*- coding: utf-8 -*-
{
    "name": "Subway Base",
    "author": "Botspot Infoware Pvt. Ltd.",
    "category": "Subway Base",
    "summary": """ """,
    "website": "https://www.botspotinfoware.com",
    "version": "18.0.1.37",
    "description": """
        RELEASE:
            [15.0.1.1]: [Add] Basic Tree view with basic details of work planning - [RM - 15 Feb],
            [15.0.1.2]: [Add] Employee Onboard - [KN - 16 Feb],
            [15.0.1.3]: [Add] One2many selection data store Many2one selection field. (context add) - [RM - 29 Feb],
                        [Add] One2many selection field in selected data show Many2one field. (domain add) - [RM - 29 Feb],
                        [Add] name search add Many2one field - [RM - 29 Feb],
            [15.0.1.4]: [ADD] [RD - 09 APR] - Added Fields and views and applied compute methods,
            [15.0.1.5]: [ADD] [RD - 10 APR] - Added changed flow and applied methods,
            [15.0.1.6]: [ADD] [RD - 15 APR] - Applied changes in methods and added new pivot view and menu,
            [15.0.1.7]: [ADD] [RD - 16 APR] - Added Geo Attendance module,
            [15.0.1.8]: [ADD] [RD - 17 APR] - View Attendance Records,
            [15.0.1.9]: [ADD] [RD - 18 APR] - Applied Changed Workflow,
            [15.0.1.10]: [ADD] [RD - 19 APR] - Applied Active Functionality,
            [15.0.1.11]: [ADD] [RD - 22 APR] - Added Security access for users and added functionality to hide buttons based on conditionaly,
            [15.0.1.12]: [UPDATE] - JS 23APR - resolved field error in employee and added store true where necessary for dashboard , pivot view.
            [15.0.1.13]: [UPDATE] [RD - 26 APR] - Modification in Week number and Current year sales average
            [15.0.1.14]: [UPDATE] [RD - 29 APR] - Modification in Current years sales average and Last yeas's sales average
            [15.0.1.15]: [ADDED] [RD - 08 May] - Added Active Employee Feature for Employee Onboard
            [15.0.1.16]: [ADDED] [RD - 08 May] - Added log tracking feature for store, store scheduling and employee onnboard
            [15.0.1.17]: [ADDED] [RD- 10 MAY] - ADDED Discuss Workflow
            [15.0.1.18]: [ADDED] [RD - 15 MAY] - Added Discuss points
            [15.0.1.19]: [ADDED] [RM - 18 JULY] - 1. Dashboard Not visible to employee,
                2.Subway not visible to employee ,
                3. in Employee Button Click on Create User if employee type is "Employee" then in base's groups of attendance assign basic level of access right, kiosk & Manual Attendance.
            [15.0.1.20]: [ADDED] [RM - 24 JULY] :
                - To solve field not found in hr.employee.public class added all the methods and field in hr.emmployee.public
            [15.0.1.21]: [ADDED] [RM - 06 AUG]:
                1. In Login page changed string and placeholder to Username from email.
                2. For Attendance Record Rule added a field and compute method in res users, to admin all
                    attandance will be visible and to manager and dist. manager all the employees of their
                    attached store and their attendance will be visible and to employee only his/her attendance will be visible.
            [15.0.1.22]: [ADDED] [RM - 10 AUG]:
                - Corrected method to fetch employee for attendance for user.
                - removed compute and added schedular 
                - also added button in store to refresh the employees.
            [15.0.1.23]: [ADDED] [RM - 14 AUG]:
                - update_store_scheduling button code merge to import_payrollsheet_button.
            [15.0.1.24]: [ADDED] [RM - 29 AUG]:
                - change label 'email address' to 'Username'.
                - Need to add new filter/group of store into attendance list view.
            [15.0.1.25]: [ADDED] [GS - 11 SEP]:
                - Added Payroll wizard as per requirement shared.
            [15.0.1.26]: [ADDED] [GS - 12 SEP]:
                - Corrected date.
            [15.0.1.27]: [ADDED] [GS - 13 SEP]:
                - Corrected Payroll Report Format as Shared.
            [15.0.1.28]: [ADDED] [RM - 3 OCT]:
                - Account No. field data type change to Char.
            [15.0.1.29]: [ADDED] [GS - 18 OCT]:
                - Added code in write of employee to update email in partner.
                - Added code in Active Employee Button to store email in partner.
                - Added Code to Create a Activity Alert for Scheduling Request.
                - Replaced Over/Short Allowed and Scheduled hours in view.
            [15.0.1.30]: [UPDATE] [GS - 21 OCT]:
                - In User wise employee Record Rule , divided into two parts for managers & For Employee.
                - Added Created By UID match to current user.
            [15.0.1.31]: [UPDATE] [GS - 24 OCT]:
                - Geo Location Store M2o .
                - Geo Location Access:
                    owner: ALL. 
                    Emp, Mng, Dist Mng: Read.
                - Store Access:
                    Owner : All.
                    Mng : Read & Write.
                    Emp : Read.
                - User:
                    Mng both: Create, Read, Write.
                - Access Group:
                    Mng both: Read, Write.
            [15.0.1.32]: [UPDATE] [RM - 26 NOV]:
                - Store scheduling data update.
            [15.0.1.33]: [UPDATE] [GS - 27 NOV]:
                - Week count on starting date instead of ending date.
            [15.0.1.34]: [UPDATE] [RM - 12 DEC]:
                - Added daily reports for attendance for DM and Admin.
                - Added TZ concept in weekly payroll
            [15.0.1.35]: [UPDATE] [GS - 13 DEC]:
                - ADDED tz in employee view and it will pass to user.
                - UPDATE - In daily report & Payroll Report made tz dynamic from employee.
            [15.0.1.36]: [UPDATE] [GS - JAN 17]:
                - Made changes in compute method, added tool tips in few with Formula.
                - Overided from view of store scheduling and made changes in that.
            [15.0.1.37]: [UPDATE] [RM - JAN 17]:
                - Created a new tree view for scheduling and added 2 new compute methods to map with main sheet : _over_or_short_food_order,_over_or_short_hours.
    """,
    "depends": ['hr','mail','hr_attendance','bsi_geo_attendance'],
    "data": [
        "security/subway_security.xml",
        "security/ir.model.access.csv",
        
        "report/payroll_report_template.xml",
        "report/payroll_report.xml",
        "report/new_hire_packet_report.xml",

        "views/email_template.xml",
        "views/dm_mail_pdf_template.xml",
        "views/store_view.xml",
        "views/geo_location_view.xml",
        "views/hr_employee_inherit_view.xml",
        "views/store_scheduling_view.xml",
        "views/store_allowed_hours_mng_view.xml",
        "views/res_users_view.xml",
        "views/hr_attendance_inherit_view.xml",
        "views/web_login.xml",
        "views/res_config_settings.xml",
        "views/menu_items.xml",
        "views/store_access_view.xml",

        "wizard/emp_payroll_entry_view.xml",
        "wizard/import_sales_entry_view.xml",
        "wizard/import_multi_store_data_view.xml",
        "wizard/update_store_scheduling_view.xml",

        "data/cron.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'bsi_subway_base/static/src/**/*',
        ],
    },
    # "images": ["static/description/Banner.gif"],
    "license": "OPL-1",
    # "price": 9.00,
    # "currency": "USD",
    "installable": True,
    "application": True,
    "auto_install": False,
}
