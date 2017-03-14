/*
 * This file is part of Vidjil <http://www.vidjil.org>,
 * High-throughput Analysis of V(D)J Immune Repertoire.
 * Copyright (C) 2013-2017 by Bonsai bioinformatics
 * at CRIStAL (UMR CNRS 9189, Université Lille) and Inria Lille
 * Contributors: 
 *     Marc Duez <marc.duez@vidjil.org>
 *     Antonin Carette <antonin.carette@etudiant.univ-lille1.fr>
 *     The Vidjil Team <contact@vidjil.org>
 * 
* "Vidjil" is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* "Vidjil" is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with "Vidjil". If not, see <http://www.gnu.org/licenses/>
*/


/**
 * GenericAxis object contain labels and their position on an axis (from 0 to 1)
 * can provide the position of an element on it
 * @constructor
 * */
function GenericAxis () {
    this.labels = [];
    this.label_mapping = {};
    this.values = [];
    this.value_mapping = {};
}

GenericAxis.prototype = {

    init : function (values, key, labels, sort) {
        this.values = values;
        if (typeof sort === 'undefined') {sort = false;}

        if (typeof key === 'function') {
            this.converter = key;
        } else {
            this.converter = function(elem) {
                return elem[key];
            }
        }

        this.populateLabels(labels);
        this.populateValueMapping();
        if (sort)
            this.labels.sort();

        return this;
    },

    populateLabels: function(labels) {
        var values = this.values;
        var label_mapping = this.label_mapping;

        if (typeof labels === 'undefined')
            this.computeLabels(values);
        else {
            for (var i=0; i < values.length; i++) {
                var value = values[i];
                var convert = this.applyConverter(value);
                if (labels.indexOf(convert) != -1 && label_mapping[convert] == undefined)
                    label_mapping[convert] = this.label("line", convert, labels.indexOf(convert), convert);
            }
        }
    },

    populateValueMapping: function() {
        var values = this.values;
        var value_mapping = this.value_mapping;
        var label_mapping = this.label_mapping;

        for (var i = 0; i < values.length; i++) {
            var value = values[i];
            var convert = this.applyConverter(value);
            if (label_mapping[convert] !== 'undefined') {
                if (value_mapping[convert] === 'undefined') {
                    value_mapping[convert] = [];
                }
                value_mapping[convert].push(value);
            }
        }
    },

    applyConverter: function(value) {
        var val;
        try {
            val = this.converter(value);
        } catch(e) {
            val = "?";
        }
        return val;
    },

    applyConverter: function(value) {
        var val;
        try {
            val = this.converter(value);
        } catch(e) {
            val = "?";
        }
        return val;
    },

    label: function (type, pos, text) {
        result = {};
        result.type = type;
        result.pos = pos;
        result.text = text;

        return result;
    },

    addLabel: function(type, value, pos, text) {
        var label = this.label(type, pos, text);
        this.label_mapping[value] = label;
        this.labels.push(label);
    },

    reset: function() {
        this.labels = [];
        this.label_mapping = {};
        this.value = [];
        this.value_mapping = {};
    },
    
    pos : function(element) {
        return this.label_mapping[this.applyConverter(element)];
    },

    computeLabels(values) {
        for (var i = 0; i < values.length; i++) {
            var value = values[i];
            var key = this.applyConverter(value);
            if (this.label_mapping[key] == undefined)
                this.addLabel("line", key, i, key);
        }
    },

    /**
     * add labels for barplot <br>
     * @param {Array} tab - barplot descriptor like the one made by Model.computeBarTab()
     * */
    computeBarLabels : function (tab) {
        this.labels = [];
        var length = Object.keys(tab).length;

        var step = 1 + Math.floor(length / NB_STEPS_BAR)

        var i=1
        for (var e in tab){
            if (i%step == 0 || (e == '?' && tab[e].length > 0)){
                var pos = this.posBarLabel(i, length);
                if (this.reverse) pos = 1 - pos;
                this.labels.push(this.label("line", pos, e));
            }
            i++;
        }

    },

    posBarLabel : function (i, length) {
        return (i-0.5)/length ;
    }
}
