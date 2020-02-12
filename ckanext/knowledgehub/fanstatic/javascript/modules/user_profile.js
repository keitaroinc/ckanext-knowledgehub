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
        Component.prototype.constructor.call(this, template);
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

    var Keyword = function(template, data){
        Component.prototype.constructor.call(this, template);
        this.tagTemplate = $('.keyword-tag-template', this.el).clone()
        $('.keyword-tag-template', this.el).remove();
        this.applyData(data);
        $('.keyword-remove', this.el).on('click', function(){
            new DeleteModal(elipsis(data.name, 30), function(){
                this.trigger('delete', data);
            }.bind(this));
        }.bind(this));
    }

    $.extend(Keyword.prototype, Component.prototype);
    $.extend(Keyword.prototype, {
        applyData: function(data){
            console.log('Keyword data:', data)
            $('.keyword-name', this.el).html(data.name);
            $.each(data.tags, function(_, tag){
                var tagEl = this.tagTemplate.clone()
                console.log('TAg', tagEl, tag.name)
                $('.keyword-tag-name', tagEl).html(tag.name);
                $('.keyword-tag-list', this.el).append(tagEl);
            }.bind(this));
        }
    });

    var Tag = function(template, data){
        Component.prototype.constructor.call(this, template);
        this.applyData(data);
        $('.tag-remove', this.el).on('click', function(){
            new DeleteModal(elipsis(data.name, 30), function(){
                this.trigger('delete', data);
            }.bind(this));
        }.bind(this));
    }

    $.extend(Tag.prototype, Component.prototype);
    $.extend(Tag.prototype, {
        applyData: function(data){
            console.log('Tag data ->', data)
            $('.tag-name', this.el).html(data.name);
        }
    });


    var UserInterests = function(){

        this.interestTypes = {
            'research_questions': {
                template: '.research-question-template',
                listSection: '.research-question-list',
                component: ResearchQuestion,
            },
            'keywords': {
                template: '.keyword-template',
                listSection: '.keywords-list',
                component: Keyword,
            },
            'tags': {
                template: '.tag-template',
                listSection: '.tags-list',
                component: Tag,
            },
        }

        api.get('user_profile_show').done(function(data){
            console.log('User Profile ->', data);
            this.profile = data.result;
            this.init();
        }.bind(this)).fail(function(err){
            console.error(err);
        })
        this.setupSelect()
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

            $.each(interests, function(interestType, values){
                $.each(values, function(_, data){
                    var config = this.interestTypes[interestType];
                    var component = this.newComponent(interestType, data);
                    $(component.el).prependTo(config.listSection);
                    this.components[interestType][data.id] = component;
                    component.on('delete', function(_, data){
                        this.deleteInterest(interestType, data);
                    }.bind(this));
                }.bind(this));
            }.bind(this));
        },
        updateInterests: function(newProfile){
            return api.post('user_profile_update', undefined, newProfile);
        },
        deleteInterest: function(interest, data){
            console.log('DeleteInterest:', interest, data)
            var profile = {
                interests: {}
            };
            profile.interests[interest] = []
            $.each(this.profile.interests[interest], function(_, entry){
                if (data.id == entry.id){
                    return;
                }
                profile.interests[interest].push(entry.id);
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
        addInterest: function(interest, data){
            if (this.components[interest] && this.components[interest][data.id]){
                return
            }

            // update the profile with API
            var profile = this.getProfile();
            profile.interests[interest].push(data.id)
            api.post('user_profile_update', undefined, profile)
                .done(function(){
                    // add component
                    var component = this.newComponent(interest, data);
                    this.components[interest] = component;
                    component.on('delete', function(_, data){
                        this.deleteInterest(interest, data)
                    }.bind(this));
                    $(component.el).appendTo(this.interestTypes[interest].listSection);
                }.bind(this))
                .fail(function(err){
                    this.flashError('Failed to update interests.')
                }.bind(this));

        },
        flash: function(message, error){

        },
        flashError: function(message){
            this.flash(message, true);
        },
        newComponent: function(interestType, data){
            var config = this.interestTypes[interestType];
            return new config.component(config.template, data);
        },
        getProfile: function(){
            var profile = {
                interests: {},
            };

            $.each(this.profile.interests, function(interest, entries){
                if (!profile.interests[interest]){
                    profile.interests[interest] = []
                }
                $.each(entries, function(_, entry){
                    profile.interests[interest].push(entry.id);
                })
            }.bind(this));

            console.log('Profile -> ', profile)
            return profile;
        },
        setupSelect: function(){
            this._setupSelect({
                selector: '.research-questions-select',
                listAction: 'research_question_list',
                interestType: 'research_questions',
                formatResult: function(data){
                    var option = $('.research-question-dropdown-option').clone();
                    $('.rq-title', option).html(data.text)
                    $('.rq-img', option).attr('src', data.image_url)
                    return option;
                },
                processResults: function(data){
                    var results = []
                        $.each(data.result.data, function(_, rq){
                            rq.text = rq.title;
                            results.push(rq)
                        });
                        return {
                            results: results
                        }
                }
            });

            this._setupSelect({
                selector: '.keywords-select',
                interestType: 'keywords',
                listAction: 'keyword_list',
            });

            this._setupSelect({
                selector: '.tags-select',
                interestType: 'tags',
                listAction: 'tag_list_search',
            });
        },
        _setupSelect: function(config){
            $(config.selector).select2({
                ajax: {
                    url: api.getUrl(config.listAction),
                    dataType: 'json',
                    type: config.type || 'GET',
                    data: config.queryData || function (term, page) {
                        return {
                            q: term, // search term
                        };
                    },
                    processResults: config.processResults || function(data){
                        var results = []
                        $.each(data.result, function(_, result){
                            result.text = result.name;
                            results.push(result)
                        });
                        return {
                            results: results
                        }
                    }
                },
                formatResult: config.formatResult
            })
            $(config.selector).click('select2:select', function(){
                var value = $(config.selector).select2("data");
                if (value){
                    this.addInterest(config.interestType, value);
                    $(config.selector).select2("data", null);
                }
            }.bind(this));
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