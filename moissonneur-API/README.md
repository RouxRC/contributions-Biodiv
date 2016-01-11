# fork from moissonneur-republique-numerique

Harvest opinions from site https://www.parlement-et-citoyens.fr/ using its JSON API.

Adapted from https://git.framasoft.org/etalab/moissonneur-republique-numerique.git by Emmanuel Raviart.

## Install

```bash
npm install
```

## Usage

### To harvest JSON files of opinions

```bash
node fetch-json.js path_of_download_directory
```

path_of_download_directory should usually be ../data-contributions
