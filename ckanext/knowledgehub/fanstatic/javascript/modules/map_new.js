ckan.module('knowledgehub-map', function(jQuery) {
  return {

    initialize: function() {

      this.initLeaflet.call(this);
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
        scrollWheelZoom: false,
        // zoomControl: false,
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

    }

  };
});