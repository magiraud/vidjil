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
 * Axis object contain labels and their position on an axis (from 0 to 1) <br>
 * can provide the position of a clone on it
 * @constructor
 * @param {Model} model 
 * @reverse {boolean} reverse - by default axis go from low to high but can be revsersed
 * */
function GermlineAxis (model, reverse) {
    this.m = model
    this.labels = [];
    this.label_mapping = {};
    this.values = [];
    this.value_mapping = {};
    this.reverse = reverse;
    GenericAxis.call(this);
}

GermlineAxis.prototype = Object.create(GenericAxis.prototype);
Object.assign(GermlineAxis.prototype, {
    
    /**
     * reset Axis
     * */
    reset: function() {
        this.labels = [];
        this.label_mapping = {};
        this.values = [];
        this.value_mapping = {};
    },
    
    /**
     * for a clone's index will return a value between 0 and 1 representing the clone's position on this axis. <br>
     * this function is empty and will be overided depending on what the axis must represent.
     * @param {integer} cloneid - clone index
     * @return {float} pos - clone's position
     * */
    pos : function(clone) {
        var pos = this.applyConverter(clone);
        return this.label_mapping[pos];
        var gene_list = this.gene_list;
        var allele_list = this.allele_list;
        var total_gene = this.total_gene;
        var pos;
        if (clone.hasSeg(this.type2)) {
            var name = clone.seg[this.type2]["name"];
            if (typeof name != 'undefined'
                && typeof gene_list[name.split("*")[0]] != "undefined")
            {
                var allele = name
                var gene = name.split("*")[0]
                var pos = this.getPos(this.gene_list[gene].rank, total_gene)

                if (this.displayAllele){
                    var total_allele = gene_list[gene].n
                    pos += (1/(total_gene+1)) * ((allele_list[allele].rank+0.5)/total_allele) - (0.5/(total_gene+1))
                }
            } else {
                pos = this.getPos(total_gene, total_gene);
            }
        }else{
            pos = this.getPos(total_gene, total_gene)
        }
        return this.label_mapping[pos];
    },
    
    /**
     * build a label descriptor
     * @param {string} type - 'line' or 'subline'
     * @param {float} pos - position on axis between 0 and 1
     * @param {string} text - text label
     * @param {string} color - label color
     * @return {object} label
     * */
    label: function (type, pos, text, color) {
        result = GenericAxis.prototype.label.call(this, type, pos, text)
        result.geneColor = color;

        return result;
    },

    addLabel: function(type, pos, text, color) {
        var label = this.label(type, pos, text, color);
        this.label_mapping[pos] = label;
        this.labels.push(label);
    },

    getPos: function(rank, total) {
        return ((rank+0.5)/(total+1));
    },

    /**
     * init axis with a germline object
     * @param {Germline} germline
     * @param {string} genetype - "V" "D" or "J"
     * @param {boolean} displayAllele - (show/hide allele)
     * */
    init: function (germline, geneType, displayAllele) {
        this.reset()
        this.germline = germline;
        var self = this;
        
        var gene_list = self.germline.gene
        var allele_list = self.germline.allele
        var total_gene = Object.keys(gene_list).length
        
        self.type2;
        if (geneType=="V") self.type2="5"
        if (geneType=="D") self.type2="4"
        if (geneType=="J") self.type2="3"
        
        //labels
        for (var key in gene_list){
            pos = self.getPos(gene_list[key].rank, total_gene)
            self.addLabel("line", pos, key, this.germline.gene[key].color);
        }
        
        if (displayAllele){
            for (var key in allele_list){
                var gene = key.split("*")[0]
                var allele = key.split("*")[1]
                var total_allele = gene_list[gene].n
                var pos = self.getPos(gene_list[gene].rank, total_gene);
                pos += (1/(total_gene+1)) * ((allele_list[key].rank+0.5)/total_allele) - (0.5/(total_gene+1))
                self.addLabel("subline", pos, "*"+allele, this.germline.allele[key].color);
            }
        }
        var pos = self.getPos(total_gene, total_gene);
        self.addLabel("line", pos, "?", "");
        self.gene_list = gene_list;
        self.allele_list = allele_list;
        self.total_gene = total_gene;
        self.displayAllele = displayAllele;
    }
})
