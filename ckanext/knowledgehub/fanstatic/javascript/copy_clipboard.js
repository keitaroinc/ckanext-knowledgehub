function copyToClipBoard() {

  var copyText = document.getElementById("copyFrom")

  copyText.select()

  document.execCommand("copy")

}

// function copyToClipBoard() {
//     var range = document.createRange();
//     range.selectNode(document.getElementById("copyFrom"));
//     window.getSelection().removeAllRanges(); // clear current selection
//     window.getSelection().addRange(range); // to select text
//     document.execCommand("copy");
//     window.getSelection().removeAllRanges();// to deselect

//     alert("clicked")
//     alert(range + "clicked")
// }
