/* ========================================================================
 * Copyright (c) 2018 Oleksandr Komarov, Modool (https://modool.pro)
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 * ======================================================================== */
odoo.define('pos_blackbox_ua.models', function (require) {
"use strict";

/* This module redefine data, which POSTed to BlockBox UA via func print_receipt(data)
 It's needed to print them in Ukrainian Fiscal Printer format.
 */

var models = require('point_of_sale.models');


models.Orderline = models.Orderline.extend({
    //used to create a json of the ticket, to be sent to the printer
    export_for_printing: function(){
        var prices = this.get_all_prices();
        return {
            quantity:           this.get_quantity(),
            unit_name:          this.get_unit().name,
            price:              this.get_unit_display_price(),
            discount:           this.get_discount(),
            product_name:       this.get_product().display_name,
            product_name_wrapped: this.generate_wrapped_product_name(),
            price_display :     this.get_display_price(),
            price_with_tax :    this.get_price_with_tax(),
            price_without_tax:  this.get_price_without_tax(),
            tax:                this.get_tax(),
            taxDetailsExt:      prices.taxDetailsExt,
            product_description:      this.get_product().description,
            product_description_sale: this.get_product().description_sale,
        };
    },
    get_all_prices: function(){
        var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
        var taxtotal = 0;

        var product =  this.get_product();
        var taxes_ids = product.taxes_id;
        var taxes =  this.pos.taxes;
        var taxdetail = {};
        var taxdetail_ext = {};
        var product_taxes = [];

        _(taxes_ids).each(function(el){
            product_taxes.push(_.detect(taxes, function(t){
                return t.id === el;
            }));
        });

        var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), this.pos.currency.rounding);
        _(all_taxes.taxes).each(function(tax) {
            taxtotal += tax.amount;
            taxdetail[tax.id] = tax.amount;
            taxdetail_ext[tax.id] = tax;
        });

        return {
            "priceWithTax": all_taxes.total_included,
            "priceWithoutTax": all_taxes.total_excluded,
            "tax": taxtotal,
            "taxDetails": taxdetail,
            "taxDetailsExt": taxdetail_ext,
        };
    },
});


// Every Paymentline contains a cashregister and an amount of money.
models.Paymentline = models.Paymentline.extend({
    //exports as JSON for receipt printing
    export_for_printing: function(){
        return {
            amount: this.get_amount(),
            journal: this.cashregister.journal_id[1],
            journal_type: this.cashregister.journal.type,
        };
    },
});


});