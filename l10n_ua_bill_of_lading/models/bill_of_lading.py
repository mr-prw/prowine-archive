# -*- coding: utf-8 -*-

from odoo import fields, models, api
from .tools.num2t4ua import num2text


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_trailer = fields.Boolean(string='Trailer')


class StockMove(models.Model):
    _inherit = 'stock.move'

    total_number_of_seats = fields.Integer(
        string='Number of seats',
        compute='_compute_total_number_of_seats')
    amount_total = fields.Float(string="Amount Total",
                                compute='_compute_amount_total')
    amount_untaxed = fields.Float(string="Amount Untaxed",
                                  compute='_compute_amount_untaxed')
    type_of_packaging = fields.Char(string='Type of packaging')
    documents_with_cargo = fields.Char(string='Documents with cargo')

    @api.multi
    def _compute_amount_untaxed(self):
        for move in self:
            move.amount_untaxed = move.sale_line_id.price_reduce_taxexcl

    @api.multi
    def _compute_amount_total(self):
        for move in self:
            move.amount_total = move.sale_line_id.price_total


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date = fields.Date(string='Date')
    vehicle_id = fields.Many2one('vehicle', string='Vehicle')
    trailer_id = fields.Many2one('trailer', string='Trailer')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    fleet_trailer_id = fields.Many2one('fleet.vehicle', string='Trailer')
    type_transportation_id = fields.Many2one('type.transportation',
                                             string='Type of transportation')
    expeditor_id = fields.Many2one('res.partner', string='Expeditor')
    driver_id = fields.Many2one('res.partner', string='Driver')
    customer = fields.Many2one('res.partner', string='Customer')
    consignor = fields.Many2one('res.partner', string='Consignor')
    consignee = fields.Many2one('res.partner', string='Consignee')
    accountant = fields.Many2one('res.partner', string='Accountant')
    leave_allowed = fields.Many2one('res.partner', string='Leave allowed')
    total_taxes = fields.Char(string='Taxes', compute='_compute_total_taxes')
    amount_untaxed = fields.Float(string='Amount untaxed',
                                  compute='_compute_amount')
    amount_total = fields.Float(string="Amount total",
                                compute='_compute_amount')
    total_number_of_seats = fields.Char(
        string='Number of seats',
        compute='_compute_total_number_of_seats')
    text_amount_total = fields.Char(string='Total amount in word',
                                    compute='_number_to_word')
    consignor_full_name = fields.Char(string='consignor',
                                      compute='_compute_full_name_consignor')
    consignee_full_name = fields.Char(string='consignee',
                                      compute='_compute_full_name_consignee')
    state_id = fields.Many2one('state',
                               string="State (Сorresponds/No corresponds)")
    text_gross_mass = fields.Char(string='Gross mass',
                                  compute='_gross_mass_to_word')

    @api.multi
    def _compute_total_taxes(self):
        for line in self:
            total = line.amount_total - line.amount_untaxed
            line.total_taxes = str(int(total)) + " грн., " + str(
                round((total - int(total)) * 100)) + ' коп.'

    @api.multi
    def _gross_mass_to_word(self):
        total = []
        for line in self:
            for move_line in line.move_lines:
                total.append(move_line.weight)
            line.text_gross_mass = num2text(int(sum(total)))

    @api.multi
    def _compute_total_number_of_seats(self):
        total = []
        for line in self:
            for move_line in line.move_lines:
                total.append(int(move_line.quantity_done))
            line.total_number_of_seats = sum(total)

    @api.multi
    def _compute_full_name_consignor(self):
        name = []
        for res in self:
            if res.consignor:
                if res.consignor.name:
                    name.append(res.consignor.name)
                if res.consignor.city:
                    name.append(res.consignor.city)
                if res.consignor.street:
                    name.append(res.consignor.street)

                res.consignor_full_name = ', '.join(name)

    @api.multi
    def _compute_full_name_consignee(self):
        name = []
        for res in self:
            if res.consignee:
                if res.consignee.name:
                    name.append(res.consignee.name)
                if res.consignee.city:
                    name.append(res.consignee.city)
                if res.consignee.street:
                    name.append(res.consignee.street)

                res.consignee_full_name = ', '.join(name)

    @api.multi
    def _number_to_word(self):
        for line in self:
            fraction = line.amount_total - int(line.amount_total)
            line.text_amount_total = num2text(
                int(line.amount_total)) + ' грн.,' + ' ' + str(
                round(fraction * 100)) + ' коп.'

    @api.model
    def _compute_amount(self):
        for line in self:
            amount_untaxed = line.sale_id.amount_untaxed
            amount_total = line.sale_id.amount_total
            line.update({
                'amount_untaxed': amount_untaxed,
                'amount_total': amount_total
            })


class Vehicle(models.Model):
    _name = 'vehicle'

    name = fields.Char(compute='_compute_name')
    vehicle_brand = fields.Many2one('vehicle.brand', string='Brand')
    vehicle_model = fields.Many2one('vehicle.model', string='Model')
    vehicle_type = fields.Many2one('vehicle.type', string='Type')
    vehicle_reg = fields.Many2one('vehicle.reg', string='Vehicle registration')

    @api.multi
    def _compute_name(self):
        names = []
        for auto in self:
            if auto.vehicle_brand.name:
                names.append(str(auto.vehicle_brand.name))
            if auto.vehicle_model.name:
                names.append(str(auto.vehicle_model.name))
            if auto.vehicle_type.name:
                names.append(str(auto.vehicle_type.name))
            if auto.vehicle_reg.name:
                names.append(str(auto.vehicle_reg.name))
            auto.name = ' '.join(names)


class VehicleBrand(models.Model):
    _name = 'vehicle.brand'

    name = fields.Char(string='Brand')


class VehicleModel(models.Model):
    _name = 'vehicle.model'

    name = fields.Char(string='Model')


class VehicleType(models.Model):
    _name = 'vehicle.type'

    name = fields.Char(string='Type')


class VehicleReg(models.Model):
    _name = 'vehicle.reg'

    name = fields.Char(string='Vehicle reg', index=True)


class Trailer(models.Model):
    _name = 'trailer'

    name = fields.Char(compute='_compute_name')
    trailer_brand = fields.Many2one('trailer.brand', string='Brand')
    trailer_model = fields.Many2one('trailer.model', string='Model')
    trailer_type = fields.Many2one('trailer.type', string='Type')
    trailer_reg = fields.Many2one('trailer.reg', string='Trailer registration')

    @api.multi
    def _compute_name(self):
        names = []
        for auto in self:
            if auto.trailer_brand.name:
                names.append(str(auto.trailer_brand.name))
            if auto.trailer_model.name:
                names.append(str(auto.trailer_model.name))
            if auto.trailer_type.name:
                names.append(str(auto.trailer_type.name))
            if auto.trailer_reg.name:
                names.append(str(auto.trailer_reg.name))
            auto.name = ' '.join(names)


class TrailerBrand(models.Model):
    _name = 'trailer.brand'

    name = fields.Char(string='Brand')


class TrailerModel(models.Model):
    _name = 'trailer.model'

    name = fields.Char(string='Model')


class TrailerType(models.Model):
    _name = 'trailer.type'

    name = fields.Char(string='Type')


class TrailerReg(models.Model):
    _name = 'trailer.reg'

    name = fields.Char(string='Trailer registration')


class TypeTransportation(models.Model):
    _name = 'type.transportation'

    name = fields.Char(string='Type of transportation')


class State(models.Model):
    _name = 'state'

    name = fields.Char(string='State')
