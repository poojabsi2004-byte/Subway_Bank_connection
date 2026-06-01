/** @odoo-module **/

/**
 * Extension of the hr_attendance systray component.
 * This patch adds custom group-based permission logic
 * to control whether a user can perform check-in/check-out actions.
 */

import { registry } from "@web/core/registry";
import { useState } from "@odoo/owl";
import { user } from "@web/core/user";

const base = registry.category("systray").get("hr_attendance.attendance_menu");

export class PatchedActivityMenu extends base.Component {
  setup() {
    super.setup();
    this.state = useState({
      canCheckInOut: false,
    });
    this.checkPermissions();
  }

  async checkPermissions() {
      const isBsiTeam = await user.hasGroup("bsi_subway_base.store_owner");
      const isAdmin = await user.hasGroup("bsi_subway_base.store_admin");

      this.state.canCheckInOut = isBsiTeam || isAdmin;
  }
}

registry
  .category("systray")
  .add(
    "hr_attendance.attendance_menu",
    { Component: PatchedActivityMenu },
    { force: true }
  );