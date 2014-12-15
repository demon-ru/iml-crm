# -*- coding: utf-8 -*-
##############################################################################
#
#    OpernERP module for Customer Relationship Management for Logistic company
#    Copyright (C) 2014 Orient Express  (<http://www.iml.oe-it.ru>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv

class crm_claim(osv.osv):
	_inherit = 'crm.claim'

	_columns = {
		'name': fields.char('Суть обращения', required=True),
		'date': fields.datetime('Дата обращения', select=True),
		'section_id': fields.many2one('crm.case.section', 'Подразделение', \
				select=True, help="Responsible sales team."\
				" Define Responsible user and Email account for"\
				" mail gateway.", track_visibility='onchange'),
		'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
		'date_deadline': fields.date('Крайний срок'),
		'color': fields.integer('Color Index'),
		
	}

	def onchange_section_id(self, cr, uid, ids, section_id, categ_id, context=None):
		vals = {}
		categs_model = self.pool.get('crm.case.categ')
		categs = categs_model.search(cr, uid, [('object_id.model', '=', 'crm.claim'),('section_id','in',[section_id, False])], context=None)
		if categ_id not in categs:
			vals['categ_id'] = None
		return {'value': vals}


	# переопределил метод из модуля crm для того, что бы значение date_closed
	# очищалось при изменение стадии из терминальной стадии
	def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):
		if not stage_id:
			return {'value': {}}
		stage = self.pool.get('crm.claim.stage').browse(cr, uid, stage_id, context=context)
		vals = {}
		if stage.is_terminate:
				vals['date_closed'] = fields.datetime.now()
		else:
			vals['date_closed'] = None
		return {'value': vals}

	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('stage_id'):
			onchange_stage_values = self.onchange_stage_id(cr, uid, ids, vals.get('stage_id'), context=context)['value']
			vals.update(onchange_stage_values)
		return super(crm_claim, self).write(cr, uid, ids, vals, context=context)


	def _resolve_section_id_from_context(self, cr, uid, context=None):
		if context is None:
			context = {}
		if type(context.get('default_section_id')) in (int, long):
			return context.get('default_section_id')
		return None

	def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
		access_rights_uid = access_rights_uid or uid
		stage_obj = self.pool.get('crm.claim.stage')
		order = stage_obj._order
		if read_group_order == 'stage_id desc':
			order = "%s desc" % order
		search_domain = []
		section_id = self._resolve_section_id_from_context(cr, uid, context=context)
		if section_id:
			search_domain += ['|', ('section_ids', '=', section_id)]
			search_domain += [('id', 'in', ids)]
		else:
			search_domain += ['|', ('id', 'in', ids), ('case_default', '=', True)]
		# perform search
		stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
		result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
		# restore order of the search
		result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
		fold = {}
		for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
			fold[stage.id] = False
		return result, fold

	_group_by_full = { 'stage_id': _read_group_stage_ids}

	def on_change_user(self, cr, uid, ids, user_id, context=None):
		""" When changing the user, also set a section_id or restrict section id
			to the ones user_id is member of. """
		section_id = None
		if user_id:
			section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
			if section_ids:
				section_id = section_ids[0]
		return {'value': {'section_id': section_id}}

class crm_claim_stage(osv.osv):
	_inherit = 'crm.claim.stage'

	_columns = {
		'is_terminate': fields.boolean('Terminate stage',
						help="Determines whether this stage is terminate or not"),
	}
