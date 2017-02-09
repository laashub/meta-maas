// Copyright 2016 Canonical Ltd.  This software is licensed under the
// GNU Affero General Public License version 3 (see the file LICENSE).

(function () {
  'use strict';

  var app = angular.module('meta-maas', ['chart.js'])

  app.controller('IndexCtrl', function($scope, metaData) {
      $scope.regions = metaData.regions;
      $scope.options = {
          legend: {
              display: true,
              position: 'right',
              labels: {
                  fontColor: '#333',
                  fontStyle: '300',
                  boxWidth: 16,
                  fontSize: 16,
                  fontFamily: 'Ubuntu, Arial, "libra sans", sans-serif',
                  padding: 20
              }
          },
          cutoutPercentage: 95,
          tooltips: {
              backgroundColor: '#333',
              bodyFontSize: 16,
              bodyFontFamily: 'Ubuntu, Arial, "libra sans", sans-serif',
              bodyFontStyle: '300',
              yPadding: 10,
              titleMarginBottom: 15
          }
      }
      $scope.colors = ['#ffb95a', '#ff8936', '#8db255', '#749f8d', '#48929b', '#a87ca0', '#dc3023', '#888888'];
      $scope.datasetOverride = [{ cutoutPercentage: 90 }]
  });

})();
