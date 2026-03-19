Extract the table from the center of the image to ASCII format. Focus only on the table, skip everything else what's not in the grid table. Try to do it in as little as possible steps.

Cells contains bold lines, draw them using ascii characters

Use '#' to draw the thick black path lines inside cells. Keep proportions reasonable (each cell same size). Return only the created ASCII art table out of the image.

Allowed symbols:

```
+-----+
|     |
|#####|
|     |
+-----+

+-----+
|  #  |
|  #  |
|  #  |
+-----+

+-----+
|  #  |
|#####|
|     |
+-----+

+-----+
|     |
|#####|
|  #  |
+-----+

+-----+
|  #  |
|###  |
|  #  |
+-----+
+-----+
|  #  |
|  ###|
|  #  |
+-----+

+-----+
|  #  |
|###  |
|     |
+-----+

+-----+
|     |
|  ###|
|  #  |
+-----+

+-----+
|     |
|###  |
|  #  |
+-----+

+-----+
|  #  |
|  ###|
|     |
+-----+
```
