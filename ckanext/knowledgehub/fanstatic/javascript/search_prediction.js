(function (_, jQuery) {
    'use strict';

    var timer = null;
    var currentFocus;

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
        /*a function to classify an item as "active":*/
        if (!x) return false;
        /*start by removing the "active" class on all items:*/
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        /*add class "autocomplete-active":*/
        x[currentFocus].classList.add("autocomplete-active");
    }
    function removeActive(x) {
        /*a function to remove the "active" class from all autocomplete items:*/
        for (var i = 0; i < x.length; i++) {
            x[i].classList.remove("autocomplete-active");
        }
    }
    function closeAllLists(elmnt) {
        /*close all autocomplete lists in the document, except the one passed as an argument:*/
        var x = document.getElementsByClassName("autocomplete-items");
        for (var i = 0; i < x.length; i++) {
            if (elmnt != x[i]) {
                x[i].parentNode.removeChild(x[i]);
            }
        }
    }

    $(document).ready(function () {
        currentFocus = -1;

        $('#field-giant-search')
            .bind("change keyup", function (event) {
                clearTimeout(timer)
                if (!(event.keyCode >= 13 && event.keyCode <= 20) && !(event.keyCode >= 37 && event.keyCode <= 40)) {
                    // detect that user has stopped typing for a while
                    timer = setTimeout(function() {
                        var text = $('#field-giant-search').val();
                        console.log('User input: ' + text)

                        if (text !== '') {
                            api.get('get_predictions', {
                                text: text
                            }, true)
                            .done(function (data) {
                                if (data.success) {
                                    closeAllLists()
                                    /*create a DIV element that will contain the items (values):*/
                                    var a, b, i;
                                    a = document.createElement("DIV");
                                    a.setAttribute("id", "autocomplete-list");
                                    a.setAttribute("class", "autocomplete-items");
                                    $('#field-giant-search').append(a);

                                    var results = data.result;
                                    results.forEach(function (r) {
                                        b = document.createElement("DIV");
                                        b.innerHTML = text;
                                        b.innerHTML += "<strong>" + r + "</strong>";
                                        b.addEventListener("click", function (e) {
                                            /*insert the value for the autocomplete text field:*/
                                            $('#field-giant-search').val(text + r);
                                            /*close the list of autocompleted values,
                                            or any other open lists of autocompleted values:*/
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

    $('#field-giant-search').on('keydown', function (e) {
        console.log(e.keyCode)
        var x = document.getElementById("autocomplete-list");
        if (x) x = x.getElementsByTagName("div");
        if (e.keyCode == 40) {
            /*If the arrow DOWN key is pressed,
            increase the currentFocus variable:*/
            currentFocus++;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 38) { //up
            /*If the arrow UP key is pressed,
            decrease the currentFocus variable:*/
            currentFocus--;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 13) {
            /*If the ENTER key is pressed, prevent the form from being submitted,*/
            // e.preventDefault();
            if (currentFocus > -1) {
                /*and simulate a click on the "active" item:*/
                if (x) x[currentFocus].click();
            }
        }
    });
})(ckan.i18n.ngettext, $);
