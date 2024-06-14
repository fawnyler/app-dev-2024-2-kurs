document.addEventListener('DOMContentLoaded', function() {
  console.log('DOMContentLoaded event fired');

  var genreItems = document.querySelectorAll('.genre-item');
  console.log('Found genre items:', genreItems);

  genreItems.forEach(function(genreItem) {
    console.log('Adding click event listener to genre item:', genreItem);

    genreItem.addEventListener('click', function() {
      console.log('Genre item clicked:', genreItem);

      var genreName = genreItem.textContent.trim();
      console.log('Genre name:', genreName);
      
      var genreUrl = '/genre/' + encodeURIComponent(genreName);
      console.log('Genre URL:', genreUrl);

      window.location.href = genreUrl;
    });
  });
});

