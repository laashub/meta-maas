var gulp = require('gulp');
var chug = require('gulp-chug');
var replace = require('gulp-replace');

gulp.task('patch-cloud', function() {
    gulp.src('./node_modules/cloud-vanilla-theme/scss/_theme.scss')
        .pipe(replace('@import \'../node_modules', '@import \'../../node_modules'))
        .pipe(gulp.dest('./node_modules/cloud-vanilla-theme/scss', { overwrite: true }));
});

gulp.task('patch-maas', function() {
    gulp.src('./node_modules/maas-gui-vanilla-theme/scss/_settings.defaults.scss')
        .pipe(replace('$asset-path: \'https://assets.ubuntu.com/v1/\';', '$asset-path: \'../assets/\';'))
        .pipe(gulp.dest('./node_modules/maas-gui-vanilla-theme/scss', { overwrite: true }));
    gulp.src('./node_modules/maas-gui-vanilla-theme/scss/build.scss')
        .pipe(replace('@import \'../node_modules', '@import \'../../node_modules'))
        .pipe(gulp.dest('./node_modules/maas-gui-vanilla-theme/scss', { overwrite: true }));
});

gulp.task('sass', ['patch-maas', 'patch-cloud'], function (done) {
    gulp.src('./node_modules/maas-gui-vanilla-theme/gulpfile.js', { read: false })
        .pipe(chug({ tasks: ['sass'] }, done));
});

gulp.task('copy', ['sass'], function () {
    var srcs = [
        './node_modules/maas-gui-vanilla-theme/build/css/build.min.css',
        './node_modules/angular/angular.min.js',
        './node_modules/angular-chart.js/dist/angular-chart.min.js',
        './node_modules/chart.js/dist/Chart.bundle.min.js'
    ];
    gulp.src(srcs).pipe(gulp.dest('./meta_maas/html/libs'));
});

gulp.task('snap-install', ['default'], function () {
    gulp.src('./meta_maas/html/**').pipe(gulp.dest(process.env.SNAPCRAFT_PART_INSTALL));
});

gulp.task('default', ['copy']);
