// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

function showValidationForm() {
   document.getElementById('validationForm').style.display = "block";
  
}

 function hideValidationForm() {
    document.getElementById('validationForm').style.display = "display:none";
 }

 function editComment() {
    document.getElementById('editComment').style.display = "block";
    document.getElementById('hideIfEdit').style.display = "display:none";
 }

(function (_, jQuery) {
   'use strict';

   var api = {
       post: function (action, data) {
          console.log(data)
           var api_ver = 3;
           var base_url = ckan.sandbox().client.endpoint;
           var url = base_url + '/api/' + api_ver + '/action/' + action;
           return $.post(url, data, 'json');
       },
       delete: function(action, data) {
         console.log(data)
         console.log(action)
         var api_ver = 3;
         var base_url = ckan.sandbox().client.endpoint;
         var url = base_url + '/api/' + api_ver + '/action/' + action;
         return $.ajax({
            url: url,
            type: 'DELETE',
            success: function(result) {
                console.log(result)
            }
        })
       },
       update: function(action, data) {
        var api_ver = 3;
        var base_url = ckan.sandbox().client.endpoint;
        var url = base_url + '/api/' + api_ver + '/action/' + action;
        return $.ajax({
            url: url,
            type: 'PUT',
            success: function(result) {
                console.log(result)
            }
        })
       }
   };

   function resourceValidationReport() {
      var resource = $('#resource').val();
       var validationWhat = $('#comment').val();
       var btn = $(this);
       console.log(btn)
       api.post('resource_validate_create', {
           what: validationWhat,
           resource: resource
       })
           .done(function (data) {
               if (data.success) {
                   btn.attr('disabled', true);
               }
           })
           .fail(function (error) {
               console.log("Add validation report: " + error.statusText);
           });
   };

   function resourceValidationDelete() {
      var resource = $('#resource').val();
       var btn = $(this);
       console.log(btn)
       console.log(resource)
       api.delete('resource_validate_delete', {
           id: resource
       })
           .done(function () {
              console.log("OKKK")
           })
           .fail(function (error) {
               console.log("Delete validation report: " + error.statusText);
           });
   };

   function resourceValidationEdit() {
    var resource = $('#resource').val();
    var validationWhat = $('#commentInput').val();
    var btn = $(this);
    console.log(btn)
    console.log(resource)
    api.update('resource_validate_update', {
         id: resource,
         what: validationWhat
     })
         .done(function () {
            console.log("OKKK")
         })
         .fail(function (error) {
             console.log("Edit validation report: " + error.statusText);
         });
 };

   $(document).ready(function () {
       var resource = $('#resource').val();
       var validationWhat = $('#comment').val();
       var validationDescription = $('#commentInput').val();
       console.log(validationWhat)
       console.log(resource)
       var validationBtn = $('#validationSubmitSuccess');
       var deleteBtn = $('#delete_validation')
       var editBtn = $('#validationEdited')
       validationBtn.click(resourceValidationReport.bind(validationBtn, validationWhat , resource));
       deleteBtn.click(resourceValidationDelete.bind(deleteBtn, resource));
       editBtn.click(resourceValidationEdit.bind(editBtn, resource , validationDescription));
       console.log(validationBtn)
   });



})(ckan.i18n.ngettext, $);