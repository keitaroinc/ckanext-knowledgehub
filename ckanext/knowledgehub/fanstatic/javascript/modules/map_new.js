ckan.module('knowledgehub-map', function(jQuery) {
  'use strict';

  var api = {
    get: function(action, params) {
      var api_ver = 3;
      var base_url = ckan.sandbox().client.endpoint;
      params = $.param(params);
      var url = base_url + '/api/' + api_ver + '/action/' + action + '?' + params;
      return $.getJSON(url);
    },
    post: function(action, data) {
      var api_ver = 3;
      var base_url = ckan.sandbox().client.endpoint;
      var url = base_url + '/api/' + api_ver + '/action/' + action;
      return $.post(url, JSON.stringify(data), 'json');
    }
  };


  return {

    initialize: function() {

      this.initLeaflet.call(this);
      this.mapResource = this.el.parent().parent().find('#map_resource');
      this.mapResource.change(this.onResourceChange.bind(this));

      $('.leaflet-control-zoom-in').css({
        'color': '#0072bc'
      });
      $('.leaflet-control-zoom-out').css({
        'color': '#0072bc'
      });
    },

    onResourceChange: function() {
      this.options.map_resource = this.mapResource.val();
      this.initializeMarkers.call(this, this.options.map_resource);
      console.log('Tuka e');

    },

    resetMap: function() {

      this.options.map_resource = this.mapResource.val();

      this.map.eachLayer(function(layer) {
        if (layer != this.osm) {
          this.map.removeLayer(layer);
        }
      }.bind(this));

      this.map.setView([39, 40], 2);
    },

    //  Initializes empty map with given default tile
    initLeaflet: function() {
      // geo layer
      var mapURL = (this.options.map_resource === true) ? '' : this.options.map_resource;

      var elementId = this.el[0].id;
      var lat = 39;
      var lng = 40;
      var zoom = 2;

      this.map = new L.Map(elementId, {
        scrollWheelZoom: true,
        zoomControl: true,
        inertiaMaxSpeed: 200,
        dragging: !L.Browser.mobile
      }).setView([lat, lng], zoom);

      var osmUrl = this.options.map_config.osm_url;
      var osmAttrib = this.options.map_config.osm_attribute;

      this.osm = new L.TileLayer(osmUrl, {
        minZoom: 2,
        maxZoom: 18,
        attribution: osmAttrib
      });

      this.map.addLayer(this.osm);

      if (mapURL) {
        // Initialize markers
        this.initializeMarkers.call(this, mapURL);
      }
    },

    initializeMarkers: function(mapURL) {

      api.post('knowledgehub_get_map_data', {
          geojson_url: mapURL
        })
        .done(function(data) {
          if (data.success) {
            var geoJSON = data.result['geojson_data'];
            this.featuresValues = data.result['features_values'];

            this.geoL = L.geoJSON(geoJSON, {

            }).addTo(this.map);
            // Properly zoom the map to fit all markers/polygons
            this.map.fitBounds(this.geoL.getBounds());
          } else {
            this.resetMap.call(this);
          }
        }.bind(this))
        .fail(function(error) {
          this.resetMap.call(this);
        }.bind(this));

    },
  };
});