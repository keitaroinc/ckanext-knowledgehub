function showSearchResults(evt, entity) {
  
    // hide elements
    tabcontent = document.getElementsByClassName("tab_content");
    for (i = 0; i < tabcontent.length; i++) {
      tabcontent[i].style.display = "none";
    }
    var x = document.getElementById(entity);
            if (x.style.display === "none") {
                x.style.display = "inline-block";
            } else {
                x.style.display = "none";
            } 
  
    document.getElementById(entity).style.display = "inline-block";
  }
