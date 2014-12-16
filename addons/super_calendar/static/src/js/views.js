openerp.super_calendar = function(instance){

	instance.web.View.include({
			load_view: function(context) {
			var self = this;
			var view_loaded_def;
			if (this.embedded_view) {
				view_loaded_def = $.Deferred();
				$.async_when().done(function() {
					view_loaded_def.resolve(self.embedded_view);
				});
			} else {
				if (! this.view_type)
					console.warn("view_type is not defined", this);
				if ((this.view_type == 'form')&&(this.dataset._model.name == 'super.calendar'))
				{
					this.dataset.get_context().__contexts[0]["id_edit_obj_for_field"] = this.dataset.ids[this.dataset.index];
					this.dataset.get_context().__contexts[0]["is_form"] = true;
					this.dataset.get_context().__contexts[1]["id_edit_obj_for_field"] = this.dataset.ids[this.dataset.index];
					this.dataset.get_context().__contexts[1]["is_form"] = true;
				}
				console.log(this.dataset.get_context());
				view_loaded_def = instance.web.fields_view_get({
					"model": this.dataset._model,
					"view_id": this.view_id,
					"view_type": this.view_type,
					"toolbar": !!this.options.$sidebar,
					"context": this.dataset.get_context(),
				});
			}
			return this.alive(view_loaded_def).then(function(r) {
				self.fields_view = r;
				if ((self.dataset._model.name == 'super.calendar')&&(self.view_type == 'form'))
				{
					if ((r.id_real_edit_obj != undefined) && (r.model_real_edit))
					{
						self.dataset.ids = [r.id_real_edit_obj];
						self.dataset._model.name = r.model_real_edit;
						self.dataset.context.model = r.model_real_edit;
						self.dataset.context.active_model = r.model_real_edit;
						self.dataset.model = r.model_real_edit;
						self.model = r.model_real_edit;
						self.session.active_id = r.id_real_edit_obj;
						self.dataset.index = 0;
						self.ViewManager.ActionManager.breadcrumbs[0].hide_breadcrumb = true
					}
				}
				// add css classes that reflect the (absence of) access rights
				self.$el.addClass('oe_view')
					.toggleClass('oe_cannot_create', !self.is_action_enabled('create'))
					.toggleClass('oe_cannot_edit', !self.is_action_enabled('edit'))
					.toggleClass('oe_cannot_delete', !self.is_action_enabled('delete'));
				return $.when(self.view_loading(r)).then(function() {
					self.trigger('view_loaded', r);
				});
			});
		},
	});

}
