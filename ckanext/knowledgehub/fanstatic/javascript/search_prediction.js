/*
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

(function (_, jQuery) {
    'use strict';

    var timer = null;
    var currentFocus;
    var searchInput = $('#field-giant-search');
    var input = document.getElementById('field-giant-search');
    var autocompleteItems = $('#autocomplete-list').find('div');

    var api = {
        get: function (action, params, async) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            params = $.param(params);
            var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
            if (!async) {
                $.ajaxSetup({
                    async: false
                });
            }
            return $.getJSON(url);
        },
        post: function (action, data) {
            var api_ver = 3;
            var base_url = ckan.sandbox().client.endpoint;
            var url = base_url + '/api/' + api_ver + '/action/' + action;
            return $.post(url, data, 'json');
        }
    };

    function addActive(x) {
        // Add active class to active item in the list
        if (!x) return false;
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        x[currentFocus].classList.add("autocomplete-active");
    }
    function removeActive(x) {
         // Remove active class from an item
        for (var i = 0; i < x.length; i++) {
            x[i].classList.remove("autocomplete-active");
        }
    }
    function closeAllLists(elmnt) {
        // Close all autocomplete lists in the document
        var x = document.getElementsByClassName("autocomplete-items");
        for (var i = 0; i < x.length; i++) {
            if (elmnt != x[i]) {
                x[i].parentNode.removeChild(x[i]);
            }
        }
        currentFocus = -1;
    }

    $(document).ready(function () {
        currentFocus = -1;

        searchInput
            .bind("change keyup", function (event) {
                clearTimeout(timer)
                if (!(event.keyCode >= 13 && event.keyCode <= 20) && !(event.keyCode >= 37 && event.keyCode <= 40) && event.keyCode != 27) {
                    // detect that user has stopped typing for a while
                    timer = setTimeout(function() {
                        var text = searchInput.val();

                        if (text !== '') {
                            api.get('get_predictions', {
                                query: text
                            }, true)
                            .done(function (data) {
                                if (data.success) {
                                    var a, b;
                                    var results = data.result;

                                    closeAllLists();

                                    a = document.createElement("DIV");
                                    a.setAttribute("id", "autocomplete-list");
                                    a.setAttribute("class", "autocomplete-items");
                                    searchInput.after(a);

                                    results.forEach(function (r) {
                                        b = document.createElement("DIV");
                                        b.innerHTML = text;
                                        b.innerHTML += "<strong>" + r + "</strong>";
                                        b.addEventListener("click", function (e) {
                                            closeAllLists();
                                            searchInput.val(text + r);
                                            searchInput.trigger("change");
                                        });
                                        a.append(b)
                                    });
                                }
                            })
                            .fail(function (error) {
                                console.log("Get predictions: " + error.statusText);
                            });
                        }
                    }, 300);
                }
            })
    });

    $('.search-input-group').on("mouseover", autocompleteItems, function(e){
        var activeItem = document.getElementsByClassName('autocomplete-active')[0];
        activeItem ? activeItem.classList.remove('autocomplete-active') : null;
        event.target !== input ? event.target.classList.add('autocomplete-active') : null;
        var p = e.target.parentElement;
        var index = Array.prototype.indexOf.call(p.children, e.target);
        activeItem ? currentFocus = index : currentFocus = -1
    });

    searchInput.on('keydown', function (e) {
        var x = document.getElementById("autocomplete-list");
        if (x) x = x.getElementsByTagName("div");

        if (e.keyCode == 40) {
            // The arrow DOWN key is pressed
            currentFocus++;
            addActive(x);
        } else if (e.keyCode == 38) {
            // The arrow UP key is pressed
            currentFocus--;
            addActive(x);
        } else if (e.keyCode == 13) {
            // ENTER key is pressed
            if (currentFocus > -1) {
                e.preventDefault();
                // simulate a click on the "active" item*
                if (x) x[currentFocus].click();
            }
        } else if (e.keyCode == 27) {
            closeAllLists();
        }
    });
})(ckan.i18n.ngettext, $);