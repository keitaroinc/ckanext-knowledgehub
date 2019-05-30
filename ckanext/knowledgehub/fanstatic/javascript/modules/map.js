ckan.module('knowledgehub-map', function(jQuery) {
  'use strict';

  //extend Leaflet to create a GeoJSON layer from a TopoJSON file
  //  L.TopoJSON = L.GeoJSON.extend({
  //    addData: function(data) {
  //      var geojson, key;
  //      if (data.type === "Topology") {
  //        for (key in data.objects) {
  //          if (data.objects.hasOwnProperty(key)) {
  //            geojson = topojson.feature(data, data.objects[key]);
  //            L.GeoJSON.prototype.addData.call(this, geojson);
  //          }
  //        }
  //        return this;
  //      }
  //      L.GeoJSON.prototype.addData.call(this, data);
  //      return this;
  //    }
  //  });
  //  L.topoJson = function(data, options) {
  //    return new L.TopoJSON(data, options);
  //  };
  String.prototype.replaceAll = function(search, replacement) {
    var target = this;
    return target.split(search).join(replacement);
  };

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
      this.mapKeyField = this.el.parent().parent().find('#map_key_field');
      this.dataKeyField = this.el.parent().parent().find('#data_key_field');
      this.dataValueField = this.el.parent().parent().find('#data_value_field');


      this.mapResource.change(this.onResourceChange.bind(this));
      this.mapKeyField.change(this.onPropertyChange.bind(this));
      this.dataKeyField.change(this.onPropertyChange.bind(this));
      this.dataValueField.change(this.onPropertyChange.bind(this));

      $('.leaflet-control-zoom-in').css({
        'color': '#0072bc'
      });
      $('.leaflet-control-zoom-out').css({
        'color': '#0072bc'
      });
    },

    onResourceChange: function() {

      this.mapKeyField.find('option').not(':first').remove();
      this.options.map_key_field = this.mapKeyField.val();
      this.options.data_key_field = this.dataKeyField.val();
      this.options.data_value_field = this.dataValueField.val();

      if (this.options.map_resource != this.mapResource.val() && this.mapResource.val() != '') {
        this.options.map_resource = this.mapResource.val();

        api.get('knowledgehub_get_geojson_properties', {
            map_resource: this.options.map_resource
          })
          .done(function(data) {
            if (data.success) {

              $.each(data.result, function(idx, elem) {
                this.mapKeyField.append(new Option(elem.text, elem.value));
              }.bind(this));

              this.resetMap.call(this);
            } else {
              this.resetMap.call(this);
            }
          }.bind(this))
          .fail(function(error) {
            ckan.notify(this._('An error occurred! Failed to load map information.'));
            this.resetMap.call(this);
          }.bind(this));
      } else {
        this.resetMap.call(this);
      }
    },

    onPropertyChange: function() {

      this.options.map_resource = this.mapResource.val();
      this.options.map_key_field = this.mapKeyField.val();
      this.options.data_key_field = this.dataKeyField.val();
      this.options.data_value_field = this.dataValueField.val();
      this.options.measure_label = 'measure label';


      if (this.options.map_key_field && this.options.data_key_field &&
        this.options.map_resource && this.options.data_value_field) {

        this.resetMap.call(this);
        this.initializeMarkers.call(this, this.options.map_resource);
      } else {
        this.resetMap.call(this);
      }
    },

    resetMap: function() {

      this.options.map_resource = this.mapResource.val();
      this.options.map_title_field = 'map title harcoded';
      this.options.map_key_field = this.mapKeyField.val();
      this.options.data_key_field = this.dataKeyField.val();
      this.options.data_value_field = this.dataValueField.val();

      this.map.eachLayer(function(layer) {
        if (layer != this.osm) {
          this.map.removeLayer(layer);
        }
      }.bind(this));

      if (this.legend) {
        this.map.removeControl(this.legend);
      }
      if (this.info) {
        this.map.removeControl(this.info);
      }
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

    createScale: function(featuresValues) {

      var colors = '#F9B7BF,#F592A0,#F26E80,#EF4A60,#B33848'.split(',');

      var values = $.map(featuresValues, function(feature, key) {
          return feature.value;
        }).sort(function(a, b) {
          return a - b;
        }),
        min = values[0],
        max = values[values.length - 1];

      return d3.scale.quantize()
        .domain([min, max])
        .range(colors);
    },
    formatNumber: function(num) {
      return (num % 1 ? num.toFixed(2) : num);
    },
    createLegend: function() {
      var scale = this.createScale(this.featuresValues);
      var opacity = 1;
      var noDataLabel = 'No data'
      this.legend = L.control({
        position: 'bottomright'
      });

      this.legend.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'info'),
          ul = L.DomUtil.create('ul', 'legend'),
          domain = scale.domain(),
          range = scale.range(),
          min = domain[0] + 0.0000000001,
          max = domain[domain.length - 1],
          step = (max - min) / range.length,
          grades = $.map(range, function(_, i) {
            return (min + step * i);
          }),
          labels = [];

        div.appendChild(ul);
        for (var i = 0, len = grades.length; i < len; i++) {
          ul.innerHTML +=
            '<li><span style="background:' + scale(grades[i]) + '; opacity: ' + opacity + '"></span> ' +
            this.formatNumber(grades[i]) +
            (grades[i + 1] ? '&ndash;' + this.formatNumber(grades[i + 1]) + '</li>' : '+</li></ul>');
        }
        ul.innerHTML +=
          '<li><span style="background:' + '#bdbdbd' + '; opacity: ' + opacity + '"></span> ' +
          noDataLabel + '</li>';

        return div;
      }.bind(this);

      this.legend.addTo(this.map);
    },
    //    createInfo: function() {
    //      var options = this.options;
    //      var self = this;
    //
    //      this.info = L.control();
    //
    //      this.info.onAdd = function(map) {
    //        this._div = L.DomUtil.create('div', 'map-info'); // create a information div
    //        this.update();
    //        return this._div;
    //      };
    //
    //      // method that we will use to update the control based on feature properties passed
    //      this.info.update = function(infoData) {
    //        this._div.innerHTML = '<h4></h4>' + (infoData ?
    //          options.map_title_field + ': ' + '<b>' + infoData.title + '</b><br/>' +
    //          options.measure_label + ': ' + '<b>' + infoData.measure + '</b>' : '');
    //      };
    //
    //      this.info.addTo(this.map);
    //    },


    initializeMarkers: function(mapURL) {

      var sqlString = $('#sql-string').val() ? $('#sql-string').val() : this.options.sql_string;
      var parsedSqlString = sqlString.split('*');
      var sqlStringExceptSelect = parsedSqlString[1];
      // We need to encode some characters, eg, '=' sign:
      sqlStringExceptSelect = sqlStringExceptSelect.replaceAll('=', '%3D');

      api.post('knowledgehub_get_map_data', {
          geojson_url: mapURL,
          map_key_field: this.options.map_key_field,
          data_key_field: this.options.data_key_field,
          data_value_field: this.options.data_value_field,
          from_where_clause: sqlStringExceptSelect
        })
        .done(function(data) {
          if (data.success) {

            var geoJSON = data.result['geojson_data'];
            this.featuresValues = data.result['features_values'];

            //          Workaround for generating color if data for only one region
            var valuesKeys = Object.keys(this.featuresValues)
            var valuesLength = valuesKeys.length;
            var scale;
            if (valuesLength === 1) {

              scale = function(value) {
                if (value == this.featuresValues[valuesKeys[0]].value) {
                  var colors = '#F9B7BF,#F592A0,#F26E80,#EF4A60,#B33848'.split(',');
                  return colors[colors.length - 1];
                }
              }.bind(this)

            } else {
              scale = this.createScale(this.featuresValues);
            }
            //             Create the info window
            //            this.createInfo.call(this);
            this.geoL = L.geoJSON(geoJSON, {
              style: function(feature) {

                var elementData = this.featuresValues[feature.properties[this.options.map_key_field]],
                  value = elementData && elementData.value,
                  color = (value) ? scale(value) : '#737373';

                return {
                  fillColor: color,
                  weight: 1,
                  opacity: 1,
                  color: color,
                  dashArray: '3',
                  fillOpacity: 0.7
                };
              }.bind(this),
              //              pointToLayer: function(fauture, latlng) {
              //                return L.marker(latlng, {
              //                  icon: smallIcon
              //                });
              //              },
              //              onEachFeature: function(feature, layer) {
              //                var elementData = this.featuresValues[feature.properties[this.options.map_key_field]];
              //
              //                if (elementData) {
              //
              //                  layer.on({
              //                    mouseover: function highlightFeature(e) {
              //                      var layer = e.target;
              //
              //                      layer.setStyle({
              //                        weight: 3,
              //                        color: '#737373',
              //                        dashArray: '3',
              //                        fillOpacity: 0.7
              //                      });
              //
              //                      if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
              //                        layer.bringToFront();
              //                      }
              //
              //                      var infoData = {
              //                        title: feature.properties[this.options.map_title_field],
              //                        measure: this.formatNumber(parseFloat(elementData['value']))
              //                      };
              //
              //                      this.info.update(infoData);
              //                    }.bind(this),
              //                    mouseout: function resetHighlight(e) {
              //                      this.geoL.resetStyle(e.target);
              //                      this.info.update();
              //                    }.bind(this)
              //                  });
              //                }
              //              }.bind(this)
            }).addTo(this.map);
            // Create the legend
            this.createLegend.call(this);
            // Properly zoom the map to fit all markers/polygons
            this.map.fitBounds(this.geoL.getBounds());
          } else {
            this.resetMap.call(this);
          }
        }.bind(this))
        .fail(function(error) {
          ckan.notify(this._('An error occurred! Failed to load map information.'));
          this.resetMap.call(this);
        }.bind(this));

    },

    //    initializeMarkers: function(mapURL) {
    //
    //          api.post('knowledgehub_get_map_data', {
    //              geojson_url: mapURL
    //            })
    //            .done(function(data) {
    //              if (data.success) {
    //                var geoJSON = data.result['geojson_data'];
    //
    //                // Create the info window
    //                this.createInfo.call(this);
    //
    //                this.geoL = L.topoJson(geoJSON, {
    //
    //                  style: function(feature) {
    //                    return {
    //                      color: '#EF4A60',
    //                      opacity: 0.5,
    //                      weight: 0.3,
    //                      fillColor: '#F37788',
    //                      fillOpacity: 0.5
    //                    }
    //                  },
    //                  onEachFeature: function(feature, layer) {
    //
    //                    if (feature.geometry.type === 'Point') {
    //
    //                      // Here we create the popups for the "Point" features
    //                      this._infoDiv = L.DomUtil.create('div', 'feature-properties');
    //
    //
    //                      this._infoDiv.innerHTML = '<h4></h4>';
    //                      $.each(feature.properties, function(idx, elem) {
    //                        this._infoDiv.innerHTML += '<b>' + idx + ': </b>' + elem + '<br/>';
    //                      }.bind(this));
    //
    //                      layer.bindPopup(this._infoDiv)
    //
    //                    } else {
    //                      // Here we create the style and info window for "Polygon" features
    //                      layer.on({
    //                        mouseover: function highlightFeature(e) {
    //                          var layer = e.target;
    //
    //                          layer.setStyle({
    //                            weight: 1.5,
    //                            color: '#404040',
    //                            dashArray: '3',
    //                            fillOpacity: 1
    //                          });
    //
    //                          if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    //                            layer.bringToFront();
    //                          }
    //                          this.info.update(feature.properties);
    //                        }.bind(this),
    //
    //                        mouseout: function resetHighlight(e) {
    //                          this.geoL.resetStyle(e.target);
    //                          this.info.update();
    //
    //                        }.bind(this)
    //                      });
    //                    }
    //                  }.bind(this)
    //                }).addTo(this.map);
    //                // Properly zoom the map to fit all markers/polygons
    //                this.map.fitBounds(this.geoL.getBounds());
    //              } else {
    //                this.resetMap.call(this);
    //              }
    //            }.bind(this))
    //            .fail(function(error) {
    //              ckan.notify(this._('An error occurred! Failed to load map information.'));
    //              this.resetMap.call(this);
    //            }.bind(this));
    //        }
  };
});