function showSearchResults(evt, entity, id) {

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
  tabs = document.getElementsByClassName("tab");
  for (i = 0; i < tabs.length; i++) {
    tabs[i].className = tabs[i].className.replace(" activateTab", "");
  }
  evt.currentTarget.className += " activateTab";



  document.getElementById(entity).style.display = "inline-block";
}
