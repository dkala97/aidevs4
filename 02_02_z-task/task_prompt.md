You are solving the "connections" puzzle using only these tools:

- connections_target
- connections_rotate
- connections_result
- connections_reset

Setup call it only once at the beginning:

1. Start by calling `connections_reset`.
2. Then call `connections_target` to get the target wiring description.

Follow this exact process:

1. Call `connections_result` to get the current wiring description.
2. Analyze the difference between target and current state.
3. Perform rotations using `connections_rotate` with cells in `RxC` format (example: `2x3`).
4. You may rotate in batches (recommended): send multiple `connections_rotate` calls at once, e.g. up to 25 rotations, then call `connections_result` to re-check the board.
5. Repeat analysis + rotations + result check until success or iteration limit.

Note: connections_target and connections_result uses vision model underneath, don't give up. Keep trying!

Success condition:

- If any `connections_rotate` response contains a token matching `{FLG:.*}`, stop immediately and return success with that flag.

Failure condition:

- If you do not reach success within 10 iterations, stop and return a clear fail message.

Rotation mechanics:

- Every rotation rotates cell 90 degrees clockwise. See all possible rotations by symbol

```

+-----+ +-----+
|     | |  #  |
|#####| |  #  |
|     | |  #  |
+-----+ +-----+

+-----+ +-----+
|  #  | |     |
|  #  | |#####|
|  #  | |     |
+-----+ +-----+

+-----+ +-----+
|  #  | |  #  |
|#####| |  ###|
|     | |  #  |
+-----+ +-----+

+-----+ +-----+
|     | |  #  |
|#####| |###  |
|  #  | |  #  |
+-----+ +-----+

+-----+ +-----+
|  #  | |  #  |
|###  | |#####|
|  #  | |     |
+-----+ +-----+

+-----+ +-----+
|  #  | |     |
|  ###| |#####|
|  #  | |  #  |
+-----+ +-----+

+-----+ +-----+
|  #  | |  #  |
|###  | |  ###|
|     | |     |
+-----+ +-----+

+-----+ +-----+
|     | |     |
|  ###| |###  |
|  #  | |  #  |
+-----+ +-----+

+-----+ +-----+
|     | |  #  |
|###  | |###  |
|  #  | |     |
+-----+ +-----+

+-----+ +-----+
|  #  | |     |
|  ###| |  ###|
|     | |  #  |
+-----+ +-----+
```

Important execution rules:

- Use only the four tools listed above.
- Always re-check board state using `connections_result` after each rotation batch.
- Be systematic: plan rotations, execute batch, verify, and iterate.
