ckan.module('user-profile', function($){
    'use strict';

    console.log('User profile load...')

    var elipsis = function(str, size){
        if (str) {
            if (str.length > size){
                return str.substring(0, size) + '...';
            }
        }
        return str;
    }

    var API = function(baseUrl){
        this.baseUrl = baseUrl;
    }

    API.prototype.getUrl = function(path, query){
        var url = this.baseUrl + '/' + path;
        if (query){
            url += '?';
            var prams = [];
            $.each(query, function(param, value){
                prams.push(param + '=' + value);
            });
            url += prams.join('&');
        }
        return url;
    }

    API.prototype.call = function(method, path, query, data){
        console.log('API CALL')
        return $.ajax({
            url: this.getUrl(path, query),
            data: data ? JSON.stringify(data) : data,
            dataType: 'json',
            method: method,
            contentType: 'application/json',
        });
    }

    API.prototype.post = function(path, query, data){
        return this.call('POST', path, query, data);
    }

    API.prototype.get = function(path, query){
        return this.call('GET', path, query);
    }


    var api = new API('/api/3/action');

    var Component = function(template){
        var tmpl = $(template)[0];
        this.el = $(tmpl).clone();
    }

    $.extend(Component.prototype, {
        on: function(event, callback){
            this.el.on(event, callback);
        },
        trigger: function(event, data){
            this.el.trigger(event, data);
        },
        applyData: function(data) {
            var el = this.el;
            $.each(data, function(selector, value){
                $(selector, el).text(value);
            });
        },
        remove: function(){
            $(this.el).remove();
        }
    });

    var ResearchQuestion = function(template, data){
        Component.prototype.constructor.apply(this, [template]);
        this.applyData(data);
        $('.research-question-remove', this.el).on('click', function(){
            new DeleteModal(elipsis(data.title, 30), function(){
                this.trigger('delete', data);
            }.bind(this))
        }.bind(this));
    }

    $.extend(ResearchQuestion.prototype, Component.prototype);
    $.extend(ResearchQuestion.prototype, {
        applyData: function(data){
            var title = data.title || '';
            if (title.length > 30){
                title = title.substring(0, 30) + '...';
            }
            var rq_data = {
                '.research-question-title': title,
                '.research-question-content': data.description,
            }
            Component.prototype.applyData.call(this, rq_data);
            $('.research-question-title', this.el)
                .attr('href', '/research-question/' + data.name)
                .attr('title', data.title);
            $('.research-question-image', this.el).attr('src', data.image_url)
        },
    });

    var UserInterests = function(){
        api.get('user_profile_show').done(function(data){
            console.log('User Profile ->', data);
            this.profile = data.result;
            this.init();
        }.bind(this)).fail(function(err){
            console.error(err);
        })
    }

    $.extend(UserInterests.prototype, {
        init: function(){
            this.components = {
                'research_questions': {},
                'keywords': {},
                'tags': {},
            }
            var interests = this.profile.interests || {
                'research_questions': [],
                'keywords': [],
                'tags': [],
            }
            $.each(interests.research_questions, function(i, researchQuestion){
                var rq = new ResearchQuestion('.research-question-template', researchQuestion);
                $(rq.el).appendTo($('.research-question-list'));
                this.components.research_questions[researchQuestion.id] = rq;
                rq.on('delete', function(_, data){
                    this.deleteInterest('research_questions', data);
                }.bind(this));
            }.bind(this));
        },
        updateInterests: function(newProfile){
            return api.post('user_profile_update', undefined, newProfile);
        },
        deleteInterest: function(interest, data){
            console.log('DeleteInterest:', interest, data)
            var profile = {};
            profile[interest] = []
            $.each(this.profile.interests[interest], function(_, entry){
                if (data.id == entry.id){
                    return;
                }
                profile[interest].push(entry.id);
            })
            this.updateInterests(profile).done(function(){
                var interest_entries = this.profile.interests[interest];
                var updated_entries = []
                $.each(interest_entries, function(_, entry){
                    if (entry.id == data.id){
                        return;
                    }
                    updated_entries.push(entry);
                }.bind(this));
                this.profile.interests[interest] = updated_entries;
                this.components[interest][data.id].remove();
                delete this.components[interest][data.id];
                this.flash('Successfuly deleted.');

            }.bind(this)).fail(function(){
                this.flashError('Unable to delete this interest. Please try again later.');
            }.bind(this));
        },
        flash: function(message, error){

        },
        flashError: function(message){
            this.flash(message, true);
        }
    });


    var DeleteModal = function(item, onYes){
        this.modal = $('#modal-delete-interest').modal({
            show: true,
        });
        $('.delete-user-interes', this.modal).text(item);
        $('#btnYes', this.modal).on('click', onYes);
    }

    $(function(){
        var userInterests = new UserInterests();
    })
});