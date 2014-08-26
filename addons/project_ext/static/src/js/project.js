openerp.project = function(openerp) {

// alex
// explanation p1.
// task may be opened in two ways
// first, through web application. This way covered in "on_card_clicked" function
// second, through direct link. This way covered by jQuery event "$(document).ready()"
// so, for one button there may be 2 hander for one event
// to prevent double triggering in each handler there are
// jQuery $('.class').off('event')
	$(document).ready( function() {
	setTimeout(function() { 
		// turning event off to prevent doubling
		// see explanation in part 1
		$('.button_url').off('click');
		// binding new event
		$('.button_url').on('click',
		function(event) {
			console.log("click event");
			return prompt("Нажмите CTL+C что бы скопировать адрес:", getUrl());
		})
	}, 1500);
	});

function getUrl() {
	console.log("Func getURL");
	var code_word = "task";
	var pure_url = document.URL;
	var last_index = pure_url.lastIndexOf(code_word);
	
	var res_url = pure_url.substring(0, last_index + code_word.length);
	return res_url;
}

    openerp.web_kanban.KanbanView.include({
        project_display_members_names: function() {
            /*
             * Set avatar title for members.
             * In kanban views, many2many fields only return a list of ids.
             * We can implement return value of m2m fields like [(1,"Adminstration"),...].
             */
            var self = this;
            var members_ids = [];

            // Collect members ids
            self.$el.find('img[data-member_id]').each(function() {
                members_ids.push($(this).data('member_id'));
            });

            // Find their matching names
            var dataset = new openerp.web.DataSetSearch(self, 'res.users', self.session.context, [['id', 'in', _.uniq(members_ids)]]);
            dataset.read_slice(['id', 'name']).done(function(result) {
                _.each(result, function(v, k) {
                    // Set the proper value in the DOM
                    self.$el.find('img[data-member_id=' + v.id + ']').attr('title', v.name).tooltip();
                });
            });
        },
        on_groups_started: function() {
            var self = this;
            self._super.apply(self, arguments);

            if (self.dataset.model === 'project.project') {
                self.project_display_members_names();
            }
        },
    });

    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function() {
			// alex
			setTimeout(function() { 
				// turning event off to prevent doubling
				// see explanation in part 1
				$('.button_url').off('click');
				// binding new event
				$('.button_url').on('click',
				function(event) {
					console.log("click event");
					return prompt("Нажмите CTL+C что бы скопировать адрес:", getUrl());
				})
			}, 1500);
            if (this.view.dataset.model === 'project.project') {
                this.$('.oe_kanban_project_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

};
