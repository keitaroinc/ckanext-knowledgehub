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
    }

    $(document).ready(function () {
        currentFocus = -1;

        searchInput
            .bind("change keyup", function (event) {
                clearTimeout(timer)
                if (!(event.keyCode >= 13 && event.keyCode <= 20) && !(event.keyCode >= 37 && event.keyCode <= 40)) {
                    // detect that user has stopped typing for a while
                    timer = setTimeout(function() {
                        var text = searchInput.val();

                        if (text !== '') {
                            api.get('get_predictions', {
                                text: text
                            }, true)
                            .done(function (data) {
                                if (data.success) {
                                    var a, b;
                                    var results = data.result;

                                    closeAllLists()

                                    a = document.createElement("DIV");
                                    a.setAttribute("id", "autocomplete-list");
                                    a.setAttribute("class", "autocomplete-items");
                                    searchInput.after(a);

                                    results.forEach(function (r) {
                                        b = document.createElement("DIV");
                                        b.innerHTML = text;
                                        b.innerHTML += "<strong>" + r + "</strong>";
                                        b.addEventListener("click", function (e) {
                                            searchInput.val(text + r);
                                            closeAllLists();
                                        });
                                        a.append(b)
                                    });
                                }
                            })
                            .fail(function (error) {
                                console.log("Get predictions: " + error.statusText);
                            });
                        }
                    }, 500);
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
                // simulate a click on the "active" item*
                if (x) x[currentFocus].click();
            }
        }
    });
})(ckan.i18n.ngettext, $);
