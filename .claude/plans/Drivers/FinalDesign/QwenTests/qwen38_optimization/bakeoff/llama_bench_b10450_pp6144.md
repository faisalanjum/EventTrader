| model                          |       size |     params | backend    | threads | n_ubatch |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | -------: | --: | --------------: | -------------------: |
| qwen35 27B Q4_K - Medium       |  15.65 GiB |    27.32 B | BLAS,MTL   |       8 |      512 |   1 |          pp6144 |         81.57 ± 0.00 |
| qwen35 27B Q4_K - Medium       |  15.65 GiB |    27.32 B | BLAS,MTL   |       8 |      512 |   1 |            tg32 |          9.77 ± 0.00 |
| qwen35 27B Q4_K - Medium       |  15.65 GiB |    27.32 B | BLAS,MTL   |       8 |     2048 |   1 |          pp6144 |         80.90 ± 0.00 |
| qwen35 27B Q4_K - Medium       |  15.65 GiB |    27.32 B | BLAS,MTL   |       8 |     2048 |   1 |            tg32 |         10.10 ± 0.00 |

build: ece963f41 (10450)
