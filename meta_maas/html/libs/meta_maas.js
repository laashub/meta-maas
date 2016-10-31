// Copyright 2016 Canonical Ltd.  This software is licensed under the
// GNU Affero General Public License version 3 (see the file LICENSE).

angular.module('meta-maas', ['chart.js'])
    .controller('IndexCtrl', function($scope, metaData) {
        $scope.regions = metaData.regions;
        $scope.options = {
            legend: {
                display: true,
                position: 'right',
                labels: {
                    boxWidth: 30,
                    fontSize: 14,
                    fontFamily: 'Ubuntu',
                }
            }
        };
    });
