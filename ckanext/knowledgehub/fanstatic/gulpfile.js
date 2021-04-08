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

var gulp = require("gulp");
var less = require("gulp-less");
var cleanCSS = require("gulp-clean-css");
var autoprefixer = require("gulp-autoprefixer");
// var sourcemaps = require('gulp-sourcemaps'); - Uncomment when developing

// Rebuild CSS from LESS
gulp.task("less", function () {
  return (
    gulp
      .src("less/main.less")
      // .pipe(sourcemaps.init()) - Uncomment when developing
      .pipe(less())
      .pipe(
        cleanCSS({
          compatibility: "ie8"
        })
      )
      .pipe(
        autoprefixer({
          browsers: ["last 5 versions", "ie >= 11"]
        })
      )
      // .pipe(sourcemaps.write()) - Uncomment when developing
      .pipe(gulp.dest("css"))
  );
});
gulp.task('fonts', function () {
  return gulp.src(['node_modules/lato-font/fonts/lato-normal/*',
                  'node_modules/lato-font/fonts/lato-medium/*',
                  'node_modules/lato-font/fonts/lato-bold/*',
                  'node_modules/lato-font/fonts/lato-heavy/*',
                  ])
    .pipe(gulp.dest('fonts'))
})

// Watch for LESS file changes
gulp.task("watch", function () {
  gulp.watch(["less/**/*.less"],
    gulp.parallel("less"));
});

// The default Gulp.js task
gulp.task('default', gulp.series('less', 'fonts', 'watch'));

