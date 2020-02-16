/**
 * JavaScript module for managing the user profile and user interests.
 */
ckan.module('user-profile', function($){
    'use strict';

    /**
     * Checks if the string has length greater than the provided size, and if so
     * it cuts the string and appends ellipsis ('...'), limitng the size of the
     * string.
     * @param {String} str the string to be checked.
     * @param {Number} size the maximal size of the string.
     */
    var ellipsis = function(str, size){
        if (str) {
            if (str.length > size){
                return str.substring(0, size) + '...';
            }
        }
        return str;
    }

    /**
     * Proxy to CKAN API actions.
     * @param {String} baseUrl the base URL of the CKAN site. 
     */
    var API = function(baseUrl){
        this.baseUrl = baseUrl;
    }

    /**
     * Returns an URL for the given path and query.
     * The query is appended as an HTTP request query.
     * 
     * @param {String} path the sub path of the API action.
     * @param {Object} query key-value object of the query parameters send to
     *  the API.
     */
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

    /**
     * Wrapper for a call to CKAN's API action.
     * 
     * @param {String} method HTTP method like 'GET', 'POST', 'PUT' etc.
     * @param {String} path the action path, like 'user_profile_show'.
     * @param {Object} query additional query parameters to be send to the API
     *  call.
     * @param {Object} data JSON data to be send in the HTTP request body.
     */
    API.prototype.call = function(method, path, query, data){
        return $.ajax({
            url: this.getUrl(path, query),
            data: data ? JSON.stringify(data) : data,
            dataType: 'json',
            method: method,
            contentType: 'application/json',
        });
    }

    /**
     * Makes a POST call to the CKAN API.
     * 
     * @param {String} path the action path, like 'user_profile_show'.
     * @param {Object} query additional query parameters to be send to the API
     *  call.
     * @param {Object} data JSON data to be send in the HTTP request body.
     */
    API.prototype.post = function(path, query, data){
        return this.call('POST', path, query, data);
    }

    /**
     * Makes a GET call to the CKAN API.
     * 
     * @param {String} path the action path, like 'user_profile_show'.
     * @param {Object} query additional query parameters to be send to the API
     *  call.
     */
    API.prototype.get = function(path, query){
        return this.call('GET', path, query);
    }


    /**
     * Proxy to CKAN's API version 3.
     */
    var api = new API('/api/3/action');

    /**
     * Base class for all UI components on the user profile page.
     * Every component has an UI template which must be present on the page. The
     * HTML of the template is cloned and bound to the component data. The
     * template is located via CSS selector.
     * 
     * @param {String} template CSS selector to locate the HTML template for this
     * Component.
     */
    var Component = function(template){
        var tmpl = $(template)[0];
        this.el = $(tmpl).clone();
    }

    $.extend(Component.prototype, {
        /**
         * Binds a handler to an event produced by this component.
         * @param {String} event the event name to bind to.
         * @param {Function} callback function to be bound as a handler to the
         * event.
         */
        on: function(event, callback){
            this.el.on(event, callback);
        },
        /**
         * Triggers an event.
         * The event name might be a custom event and additional data can be
         * passed along to the handler.
         * @param {String} event the name of the event to be triggered.
         * @param {Any} data additional event data to be passed to the handlers.
         */
        trigger: function(event, data){
            this.el.trigger(event, data);
        },
        /**
         * Performs a one way binding of the data to the elements in the Component
         * DOM.
         * The keys in the data represent a CSS selector to which to bind the
         * data to. The value is set as 'text' to the selected HTML element.
         * @param {Object} data the data to bind to the component elements.
         */
        applyData: function(data) {
            var el = this.el;
            $.each(data, function(selector, value){
                $(selector, el).text(value);
            });
        },
        /**
         * Removes this Component from the window DOM.
         */
        remove: function(){
            $(this.el).remove();
        }
    });

    /**
     * UI component representing a Research Question interest.
     * @param {String} template CSS selector to specify the research question
     * HTML template.
     * @param {Object} data research question data.
     */
    var ResearchQuestion = function(template, data){
        Component.prototype.constructor.call(this, template);
        this.applyData(data);
        $('.research-question-remove', this.el).on('click', function(){
            new DeleteModal(ellipsis(data.title, 30), function(){
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

    /**
     * UI component for a Keyword interest.
     * @param {String} template CSS selector to specify the keyword HTML template.
     * @param {Object} data the keyword data. 
     */
    var Keyword = function(template, data){
        Component.prototype.constructor.call(this, template);
        this.tagTemplate = $('.keyword-tag-template', this.el).clone()
        $('.keyword-tag-template', this.el).remove();
        this.applyData(data);
        $('.keyword-remove', this.el).on('click', function(){
            new DeleteModal(ellipsis(data.name, 30), function(){
                this.trigger('delete', data);
            }.bind(this));
        }.bind(this));
    }

    $.extend(Keyword.prototype, Component.prototype);
    $.extend(Keyword.prototype, {
        applyData: function(data){
            $('.keyword-name', this.el).html(data.name);
            $.each(data.tags, function(_, tag){
                var tagEl = this.tagTemplate.clone()
                $('.keyword-tag-name', tagEl).html(tag.name);
                $('.keyword-tag-list', this.el).append(tagEl);
            }.bind(this));
        }
    });

    /**
     * UI component for a Tag interest.
     * @param {String} template CSS selector to specify the tag HTML template.
     * @param {Object} data the Tag data. 
     */
    var Tag = function(template, data){
        Component.prototype.constructor.call(this, template);
        this.applyData(data);
        $('.tag-remove', this.el).on('click', function(){
            new DeleteModal(ellipsis(data.name, 30), function(){
                this.trigger('delete', data);
            }.bind(this));
        }.bind(this));
    }

    $.extend(Tag.prototype, Component.prototype);
    $.extend(Tag.prototype, {
        applyData: function(data){
            $('.tag-name', this.el).html(data.name);
        }
    });


    /**
     * Represents the user interests on the user profile page.
     * 
     * Manages adding/removing and updating the user interests in Research Questions,
     * Tags and Keywords.
     * 
     * Once instantiated, it will load the user profile and then will display
     * the user interests, such as Research Questions, Keywords and Tags.
     */
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
            this.profile = data.result;
            this.init();
        }.bind(this)).fail(function(err){
            this.flashError('Failed to load interests.')
        }.bind(this))
        this.setupSelect()
    }

    $.extend(UserInterests.prototype, {
        /**
         * Initializes and binds the components to the user profile page.
         */
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
        /**
         * Updates the user interests by updating the user profile via CKAN's
         * API.
         * @param {Object} newProfile the updated user profile to be saved.
         */
        updateInterests: function(newProfile){
            return api.post('user_profile_update', undefined, newProfile);
        },
        /**
         * Deletes an interest and updates the UI on the user profile page.
         * @param {String} interest the user interests. Possible values are:
         * 'research_questions;, 'tags' or 'keywords'.
         * @param {Object} data the interest data.
         */
        deleteInterest: function(interest, data){
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
        /**
         * Adds a user interest and updates the UI on the user profile page.
         * @param {String} interest the user interests. Possible values are:
         * 'research_questions;, 'tags' or 'keywords'.
         * @param {Object} data the interest data.
         */
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
        /**
         * Flashes a message in the user profile page.
         * @param {String} message the message to flash to the user.
         * @param {Boolean} error whether this message is an error message. 
         */
        flash: function(message, error){

        },
        /**
         * Flashes an error message to the user.
         * @param {String} message the error message to be flashed to the user.
         */
        flashError: function(message){
            this.flash(message, true);
        },
        /**
         * Creates new UI component based on the registered UI components.
         * 
         * This is a factory method for creating UI components with default
         * configuration.
         * @param {String} interestType type of UI component like: 'research_questions',
         * 'tags' or 'keywords'. 
         * @param {Object} data the user interest data for the component to be
         * displayed.
         */
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

            return profile;
        },
        /**
         * Sets up the autocomplete select dropdowns for all interests.
         */
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


    /**
     * Creates new Modal popup to be displayed before deleting an interest.
     * @param {String} item the title of the item.
     * @param {Function} onYes handler to be called when the user confirms the
     * deletion of the selected item.
     */
    var DeleteModal = function(item, onYes){
        this.modal = $('#modal-delete-interest').modal({
            show: true,
        });
        $('.delete-user-interes', this.modal).text(item);
        $('#btnYes', this.modal).on('click', onYes);
    }

    $(function(){
        new UserInterests();
    })
});