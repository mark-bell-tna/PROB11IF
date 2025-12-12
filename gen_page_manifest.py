import json
import os
from read_page_xml import pageXML

# head copy1_60_data_map.tsv 
# COPY 1/60/1     TranskribusXML/p001.xml N       C15163751       JELYQXNBVBMYKEPOUFQUZJUW
# COPY 1/60/2     TranskribusXML/p002.xml Y       C15163752       IHKZVRZJLVJFEIFAGFGCCJOD
# COPY 1/60/3     TranskribusXML/p003.xml Y       C15163753       TVRDLSRBPGZTIRVTWTENTVUS
data_map_file = open("SOURCEDATA/copy1_60_data_map.tsv", "r")

cat_data = json.load(open("SOURCEDATA/edit_C325807_catalogue_structure.json", "r"))

# head xml_region_names.json
# {
#  "p001.xml": {
#   "r_1": "DescriptionText",
#   "r": null,
#   "r_4": "FormCompleted",
#   "r_2": "CopyrightOwner",
#   "r_3": "CopyrightAuthor"
#  },
region_data = json.load(open("SOURCEDATA/xml_region_names.json", "r"))

data_lookup = {}
for row in data_map_file:
    fields = row[:-1].split("\t")
    cat_ref = fields[0].replace(" ", "")
    if cat_ref not in data_lookup:
        data_lookup[cat_ref] = []
    data_lookup[cat_ref].append(fields)

manifest_list = []
counter = 0
for catalogue_ref, data_rows in data_lookup.items():
    form_row = None
    photo_row = None


    for row in data_rows:
        PX = pageXML(row[1])
        if PX.region_count > 3 and form_row is None:
            form_row = row
        if len(data_rows) > 1:
            for reg in PX:
                if reg.region_type == 'image' and photo_row is None:
                    photo_row = row

    if form_row is None:
        continue
    if form_row[3] == '':
        continue
    counter += 1
    FormX = pageXML(form_row[1])
    form_key = form_row[4]
    photo_region = None
    photo_key = None
    if photo_row is not None:
        PhotoX = pageXML(photo_row[1])
        photo_key = photo_row[4]
        for reg in PhotoX:
            if reg.region_type == 'image':
                photo_region = reg
                break

    FULL_IMAGE_ID = f"https://files.transkribus.eu/iiif/2/{form_key}/full/full/0/default.jpg"
    if photo_key is not None:
        PHOTO_IMAGE_ID = f"https://files.transkribus.eu/iiif/2/{photo_key}/{photo_region.left},{photo_region.top},{photo_region.width},{photo_region.height}/full/0/default.jpg"
    else:
        PHOTO_IMAGE_ID = None
   
    cat_entry = cat_data[form_row[3]]
    catalogue_ref = form_row[0].replace(" ", "")
    description_fields = cat_entry['DescriptionFields']
    description_fields['DescriptionText'] = cat_entry['DescriptionText']
    manifest_id = f"https://example.org/iiif/manifest/{catalogue_ref}.json"
    canvas_id = f"https://example.org/iiif/canvas/{catalogue_ref}"
    annotationpage_id = f"https://example.org/iiif/annotationpage/{catalogue_ref}"
    image_annotation_id = f"https://example.org/iiif/annotation/{catalogue_ref}"
    supplement_page_id = f"https://example.org/iiif/annotation/{catalogue_ref}/supplementing" # no longer used
    regions_page_id = f"https://example.org/iiif/{catalogue_ref}/regions"
    link_annotation_base = f"https://example.org/iiif/anno/{catalogue_ref}-link"  # could be used with dataset of contextual links

    region_annotations = []

    for idx, reg in enumerate(FormX, start=1):
        region_field = region_data[FormX.file_name.name].get(reg.id, None)
        if region_field is None:
            continue
        if region_field not in description_fields:
            continue
        field_value = description_fields[region_field]
        

        #Add regions with labels and tags/descriptions
        region_annotation_id = f"https://example.org/iiif/annotation/{catalogue_ref}/region-{idx}"
        target = f"{canvas_id}#xywh={int(reg.left)},{int(reg.top)},{int(reg.width)},{int(reg.height)}"

        region_annotations.append({
            "id": region_annotation_id,
            "type": "Annotation",
            "motivation": "commenting",
            "label": { "en": [field_value] },
            "target": target,
            "body": [
                {
                    "type": "Text",
                    "value": region_field,
                    "purpose": "tagging"
                },
                {
                    "type": "Text",
                    "value": field_value,
                    "purpose": "describing"
                }
            ]
        })


        #Add attached image as annotation
        # Probably don't need this
        #if photo_key is not None:

        paint_items = [{
                "id": image_annotation_id,
                "type": "Annotation",
                "motivation": "painting",
                "body": {
                    "id": FULL_IMAGE_ID,
                    "type": "Image",
                    "format": "image/jpeg",
                    "width": 3508,
                    "height": 2479,
                    "service": [
                        {
                          "id": f"https://files.transkribus.eu/iiif/2/{form_key}",
                          "type": "ImageService3",
                          "profile": "level1"
                        }
                      ]
                },
                "target": canvas_id,
            }]

        # Add a layer for the photo if it is a fold aside one
        if photo_key is not None:
            paint_items.append({
                "id": image_annotation_id + "/photo",
                "type": "Annotation",
                "motivation": "painting",
                "body": {
                    "id": PHOTO_IMAGE_ID,
                    "type": "Image",
                    "format": "image/jpeg",
                    "width": photo_region.width,
                    "height": photo_region.height
                },
                "target": canvas_id + f"#xywh=100,100,{photo_region.width},{photo_region.height}",  # ideally x,y align with the actual image position but requires more work to line it up
            })

    #Build manifest
    annotation_list = []
    annotation_list.append({"id" : regions_page_id, "type" : "AnnotationPage", "items": region_annotations})
    this_item = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": manifest_id,
        "type": "Manifest",
        "label": {"en": [catalogue_ref]},
        "items": [
            {
            "id" : canvas_id,
            "type" : "Canvas",
            "label" : {"en" : [catalogue_ref]},
            "width" : 3508,
            "height" : 2479,
            "items" : [
                {
                    "id" : annotationpage_id,
                    "type" : "AnnotationPage",
                    "items" : paint_items
                }] ,
             "annotations" : [
                 {
                     "id" : regions_page_id,
                     "type" : "AnnotationPage",
                     "items" : region_annotations
                 }
             ]
        }]
    }

    #Save JSON
    output_dir = "./MANIFESTS/"
    outname = catalogue_ref.replace("/", "_") + ".json"

    # Metatdata for the Collection manifest
    manifest_list.append({
      "id": f"https://raw.githubusercontent.com/mark-bell-tna/COPY1IIF/refs/heads/main/MANIFESTS/{outname}",
      "type": "Manifest",
      "label": {
        "en": [catalogue_ref]
      },
       "thumbnail": [
            {
              "id": f"https://files.transkribus.eu/iiif/2/{form_key}/full/200,/0/default.jpg",
              "type": "Image",
              "format": "image/jpeg",
              "width": 200
            }
          ]
    })
    output_path = os.path.join(output_dir, outname)

    with open(output_path, "w", encoding="utf-8") as f:
            json.dump(this_item, f, indent=2, ensure_ascii=False)

main_manifest = {
  "@context": "http://iiif.io/api/presentation/3/context.json",
  "id": "https://example.org/iiif/collection/copy1-forms.json",
  "type": "Collection",
  "label": {
    "en": ["Copy1/60"]
  },
  "items": manifest_list
}

output_path = os.path.join(output_dir, "COPY_1_60.json")
with open(output_path, "w", encoding="utf-8") as f:
        json.dump(main_manifest, f, indent=2, ensure_ascii=False)
