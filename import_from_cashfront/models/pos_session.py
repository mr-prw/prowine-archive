import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    start_at = fields.Date(string='Opening Date', readonly=True)

    @api.constrains('user_id', 'state')
    def _check_unicity(self):
        # open if there is no session in 'opening_control', 'opened', 'closing_control' for one user
        if self.search_count([
            ('state', 'not in', ('closed', 'closing_control')),
            ('user_id', '=', self.user_id.id),
            ('rescue', '=', False)
        ]) > 1:
            _logger.warning("You cannot create two active sessions with the same responsible!")

    @api.constrains('config_id')
    def _check_pos_config(self):
        if self.search_count([
            ('state', '!=', 'closed'),
            ('config_id', '=', self.config_id.id),
            ('rescue', '=', False)
        ]) > 1:
            _logger.warning("Another session is already opened for this point of sale.")
