// Adobe Photoshop — open in ExtendScript Toolkit or File > Scripts > Browse
// Assembles layers/*.png into sage_cast_b_layers.psd (2048x2048)
(function () {
  var root = new File($.fileName).parent;
  var layersDir = new Folder(root + "/layers");
  var doc = app.documents.add(2048, 2048, 72, 'sage_cast_b', NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
  var names = [
    "body",
    "inner_torso",
    "inner_collar",
    "inner_accessory",
    "coat_back",
    "coat_body",
    "coat_lapel_R",
    "coat_lapel_L",
    "coat_pocket",
    "pin_capsule",
    "hair_back",
    "hair_side_L",
    "hair_side_R",
    "hair_front",
    "hair_extra",
    "face_base",
    "nose",
    "mouth_base",
    "mouth_open_a",
    "mouth_open_i",
    "mouth_open_u",
    "mouth_open_e",
    "mouth_open_o",
    "eye_white_L",
    "eye_iris_L",
    "eye_highlight_L",
    "eye_lash_L",
    "eye_white_R",
    "eye_iris_R",
    "eye_highlight_R",
    "eye_lash_R",
    "brow_L",
    "brow_R",
    "expr_e1_smile",
    "expr_e2_thinking",
    "expr_e3_empathy",
    "expr_e4_surprise",
    "expr_e5_nod",
  ];
  for (var i = 0; i < names.length; i++) {
    var f = new File(layersDir + "/" + names[i] + ".png");
    if (!f.exists) { $.writeln('missing ' + f); continue; }
    app.open(f);
    app.activeDocument.selection.selectAll();
    app.activeDocument.selection.copy();
    app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
    doc.paste();
    doc.activeLayer.name = names[i];
  }
  var out = new File(root + "/sage_cast_b_layers.psd");
  var psd = new PhotoshopSaveOptions();
  doc.saveAs(out, psd, true);
  $.writeln("saved " + out);
})();
