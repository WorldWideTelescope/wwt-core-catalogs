# wwt-core-catalogs

The purpose of this repository is to manage the image data comprising WWT's core
data holdings. Three major applications are maintenance of the WWT "legacy"
WTML/XML metadata files, automating the ingestion of the core data in the
Constellations system, and automating the ingestion of new content that's not
yet in Constellations *or* the legacy system.

Python package requirements of note:

- `wwt_data_formats` >= 0.17
- `wwt_api_client` >= 0.5


## Approach: Legacy System

A major goal of this repo is create a group of WTML and XML files that can be
uploaded directly to WWT's cloud storage to define WWT’s "legacy" core data
holdings. These files are made available through the `catalog.aspx` API
endpoint: the file `exploreroot6.wtml` is downloaded from

#### http://worldwidetelescope.org/wwtweb/catalog.aspx?W=exploreroot6

and so on.

Each of these WTML files defines a collection consisting of at least one
"folder" that may contain imagesets, "places", references to other folders, or
directly included nested folders, among other things. The structure of each
collection is defined by a YAML file in `catfiles/`; e.g.
`catfiles/exploreroot6.yml` defines the structure of the `exploreroot6.wtml`
output.

The particular names and relationships between various folders are longstanding
conventions that can't be changed lightly. Backwards compatibility is also an
issue. For instance, version 5.x clients load up `exploreroot.wtml` (NB: no "6")
and from thence files like `mars.wtml`, so these can't contain HiPS datasets
since the clients will reject the unrecognized dataset types.

In the folder YAML, `children` is a list of folder contents. Each entry can be:

- A dict, indicating a sub-folder
- A string of the form `imageset <URL>`, indicating the imageset associated with
  the given image data URL
- A string of the form `place <UUID>`, indicating the Place associated with the
  given UUID

Places are defined in `places/*.yml`, organized by dataset type and longitude
for convenience. Each item in a place's YAML dictionary corresponds fairly
directly to a WTML XML attribute or child element, except imagesets are once
again referenced by URL. Places are assigned random UUIDv4s because there's no
entirely sensible way to uniquely distinguish places, since their coordinates
matter a lot and those are floating-point numbers. The UUIDs aren't exposed
outside of this repo.

Imagesets are defined in `imagesets/*.xml`, organized by dataset type, reference
frame, and bandpass. Imagesets are uniquely identified by their data URLs. The
XML contents correspond directly to the WTML imageset representation.

In the current model there are two root catalog files: `exploreroot6.wtml` and
`imagesets6.wtml`. All other WTMLs are reachable from `exploreroot6`, which
populates the root of the client's "Explore" ribbon. The `imagesets6` file
defines the built-in imagesets accessible from the `Imagery:` dropdown. So it
shouldn't get too large.

The directory `sad_imagesets/` contains a structure like `imagesets/`, but with
known imagesets that shouldn't be used due to bad coordinates and the like.
Known problematic datasets should be moved there so that we don't lose track of
them. Add a `_Reason` attribute documenting why the imageset has a problem.
Sometimes the underlying data could in principle be rescued (e.g. the astrometry
of a study is just poor), sometimes not really (a planetary map is backwards).


## Approach: Constellations

Building on top of the system described above, there is a further framework
aimed at ingesting data from this repository into the WWT Constellations system.

Metadata about imagesets and places are extracted into files in the `cxprep/`
directory, which stores information in large text files, one for each
Constellations "handle" that is intended to eventually host the associated data.

By default, each record is marked with a `wip: yes` flag, indicating that the
record is a “work in progress” and should not be uploaded. After the information
have been validated and corrected, this flag can be removed, and the
`register-cxprep` command can be used to register the new items in the
Constellations system.

After this is done, the core database is updated with Constellations metadata,
for posterity and to help make sure that work isn't duplicated.


## Approach: AstroPix

We are also integrating with AstroPix, which indexes many of the same images
that can or should be found in WWT. To use the routines for cross-matching WWT's
holdings to the AstroPix collection, download the AstroPix database as one big
JSON file:

```sh
curl -fsSL "https://www.astropix.org/link/39po?format=json" -o astropix/all.json
```

(This link goes to a saved search that will match everything in the AstroPix
database: "publisher ID is not adsdadasdasdas", basically.)


## Main Driver

Most operations are driven from the script `./cattool.py`, which has as Git-like
subcommand interface.


### `cattool emit`

The `emit` subcommand emits the WTML and XML files into the current directory.
This traces through the different collection definititions, expanding out XML
for places and imagesets. The `--preview` option emits `foo_rel.wtml` files with
relative URLs for the folder cross-references, allowing local previewing of the
catalog files using `wwtdatatool serve`.

(To preview locally in the webclient, you must edit `dataproxy/Places.js` to
replace the reference to `webclient-explore-root.wtml` to a locally-served
version. The webclient gets confused if you try to load `exploreroot6` as a
separate collection.)

(To preview locally in the Windows client, you also need to run a hacked custom
build, or maybe to monkey with your client's local cache.)

When a data update is ready to issue, these files should be able to be uploaded
directly into the `catalog` blob container of the `wwtfiles` storage account.
This can be done from the command line with something like this:

```sh
export AZURE_STORAGE_CONNECTION_STRING=secret-for-wwtfiles
az storage azcopy blob upload -c catalog -s jwst.wtml
```

After that:

- the `wwt6_login.txt` file needs to be updated to trigger the clients to pull
  down the new data,
- the Windows release datafiles cabinet needs to be updated to include the new
  data, and
- a new Windows release needs to be made including the updated cabinet

When the `imagesets6.xml` file is updated, the `builtin-image-sets.wtml` file
should be updated as well:

```sh
export AZURE_STORAGE_CONNECTION_STRING=secret-for-wwtwebstatic
az storage azcopy blob upload -c '$web' -s imagesets6.xml -d engine/assets/builtin-image-sets.wtml
```

The `wwtweb-prod` CDN endpoint should then have that path purged. (Probably we
should stop updating this file and change our code to use `imagesets6` instead,
but that migration would be a bit of a hassle.)


### `cattool emit-searchdata`

The `emit-searchdata` subcommand emits a JavaScript/JSON data file used as a
search index by the web client. It indexes not only the sky-based image sets,
but also several catalogs of well-known stars and galaxies (e.g., the Messier
and Bright Star catalogs).

The command takes one argument, which is the name of a directory containing
supporting catalog data files. These can be pulled off of the `catalog` blob
container of the `wwtfiles` storage account, or downloaded like so:

```sh
for c in bsc commonstars constellationlist ic messier ngc ssobjects ; do
  curl -fsSL "http://worldwidetelescope.org/wwtweb/catalog.aspx?Q=$c" -o $c.txt
done
```

After downloading, one should currently patch some of the files with the patch
`assets/repair-catalogs.patch` stored in this repo. The more sensible thing
would be to actually fix the server-side catalogs, but maintaining/regenerating
them is a bigger project than I want to take on right now (PKGW, July 2022).
Note that "fixing" is a bit ill-defined; the patch updates the BSC to add
RA/Decs to items in the HR catalog that are now known to be novae, etc., which
should maybe be removed instead. (Historical webclient behavior, though, was to
provide these sources in a way that wedges the viewer if you try to seek to
one.)

The `--pretty-json` option causes the data to be emitted to stdout as indented,
prettified JSON, which is most convenient for diffing and understanding the
detailed output. Without this option, the output is essentially minified
JavaScript, emitted using [pyjson5] and some manually-inserted shims.

[pyjson5]: https://github.com/Kijewski/pyjson5

The non-pretty output is currently put into production by uploading it into the
path `$web/data/searchdata_v2.min.js` path of the `wwtwebstatic` storage account
on Azure. A CDN purge will be needed to update the search data for the
production webclient. The upload can be done from the CLI with:

```sh
export AZURE_STORAGE_CONNECTION_STRING=secret-for-wwtwebstatic
az storage azcopy blob upload -c '$web' -s searchdata_v2.min.js -d data/
```


### `cattool ingest --cx-handle=HANDLE <WTML>`

This reads a WTML file and updates `places/`, and `imagesets/` with its data
contents. If you have a WTML defining new datasets to include, use this.

The `--cx-handle` option specifies which Constellations handle the new imagery
will eventually be associated with. Use `skip` as a value if the images should
not go into Constellations. If the imagery should go to multiple handles, edit
the resulting files to change the `Xcxstatus` `queue` setting as appropriate. At
some point after you run this command, run `cattool update-cxprep` to transfer
the appropriate information into the `cxprep/` files for the next stage of
Constellations ingest. To guard against typos, this command requires that a
`cxprep/{HANDLE}.txt` file already exists; to add entries for a new handle,
create that file as an empty text file before running the command.

With the `--prepend-to=FILENAME` option, this command will update an existing
catalog template file to include the newly-ingested imagery at its beginning.
For instance, the command:

```sh
./cattool.py ingest jwst_fgs_preview.wtml --prepend-to=catfiles/jwst.yml --cx-handle=jwst
```

will take the new images and places defined in the file `jwst_fgs_preview.wtml`,
incorporate their definitions into the database, and add the new images at the
beginning of the `jwst` catalog.

With the `--emit` option, this command will create a wholly new catalog template
in `catfiles/` mirroring the input WTML's structure. You'll only want this
option if you're importing a substantial, new image collection.


### `cattool update-astropix`

This command updates the `imagesets/` files with automatable cross-matches to
the AstroPix database, and emits information about AstroPix imagery that
couldn't be matched to anything in the WWT corpus. In general, anything in
AstroPix with detailed WCS should be findable *somewhere* in the WWT catalogs.


### `cattool update-cxprep`

This command updates the Constellations "prep" files in the `cxprep/`
subdirectory with any new records that have been ingested into the main
database.

After running it, you should see any new records appended to the appropriate
`cxprep/<handle>.txt` text file, with `wip: yes` flags indicating that they
still need review.


### `cattool [--dry-run] register-cxprep`

This command scans the Constellations "prep" files in the `cxprep/` subdirectory
and registers any images or scenes that have been marked as ready to ingest.
After completion, those records are removed from the "prep" files, and the main
database is updated to log the Constellations IDs of the new assets.

It is very important that after this step is run, a pull request is filed
containing the database updates. Otherwise, we could end up with redundant
Constellations records for the different items, and people will duplicate work.

In `--dry-run` mode, everything is done except for the actual registrations, and
the `cxprep/` files are not rewritten. If anything was fake-registered, *you
must make sure to throw away the changes* in `imagesets/` and `places/` since
they will contain fake IDs!

In order to actually do the registration, you will need to have a Constellations
login with the appropriate permissions on the handles to be modified. In order
to create new handles, one needs Constellations "superuser" permissions.

After registering with Constellations, you should review the new items there to
validate that they look like you expect. The most important thing to check is
that the bounding boxes and backgrounds of the new scenes are good; those are
the things that you can't control before the Constellations items are created.


### `cattool forget <URL> [URLs....]`

Rewrite the main files to remove one or more imagesets by their URLs. Any places
referencing those imagesets are removed, and any folders referencing those places
or imagesets have those entries removed.

This command is mainly meant to be used to remove duplicated imagesets. Ones
that are busted in some way should ideally have their information logged into
the `sad_imagesets` directory.

If the removed imagesets are listed somewhere in the `cxprep/` tree, you should
regenerate those files with the `update-cxprep` command to remove them from
those files.

The code that rewrites the folder YAML files unfortunately removes any comments
that were in place. You should avoid committing spurious or undesired changes
to such comments by putting them back, either manually or with a command like
`git add -p`.


### `cattool report`

Report the number of imagesets in the database.


### `cattool trace`

Trace down from `exploreroot6` and `imagesets6` to search for imagesets that are
not referenced from any WTML collections. This indicates the presence of a known
imageset that isn't accessible by the clients (with a small number of known
false positives).


### `cattool format-imagesets`

Read and rewrite the files in `imagesets/`, applying the system's organization
and normalization. E.g., if you edit an imageset's bandpass setting, it will
move into a new file.


### `cattool format-places`

Like `format-imagesets`, but for places.


### `cattool ground-truth`

For each of the catalogs currently being managed by this repo, download the
version that's currently being served by the production server and save it into
the current directory. You can combine this with a temporary Git repository or
other diffing solution in order to review the updates that you'll be uploading.


### `cattool prettify <XML>`

Rewrite an XML file in "prettified" format, assuming that elements have lots of
attributes. This is a low-level utility.


### `cattool replace-urls <SPEC-PATH>`

A specialized, untested utility intended to update imageset URLs in a compatible
way by using WWT's AltUrl support.


### `cattool add-alt-urls <SPEC-PATH>`

A specialized utility to add AltUrl attributes to many imagesets at once.


### `cattool partition <PARTITION-PATH>`

A specialized utility for partitioning images of the sky into different
categories.


### `cattool emit-partition <PARTITION-PATH> <NAME> <WTML-PATH>`

A specialized utility for emitting a WTML file containing records based on a
"partition file" as used in `cattool partition`. The point of this tool is to
create an input that can be used with the WWT Constellations `update_handle.py`
script to gradually import data from the core corpus into the Constellations
system.


## Data Ingest Pipeline

Steps to ingest new data are driven from the script `./pipeline.py`, which also
has as Git-like subcommand interface. It is derived from the [Toasty Pipeline]
framework but adds in elements from the `cxprep` framework as well. Note that
this framework is intended for *new* images that haven’t yet been ingested into
the local databases (e.g., `imagesets` and `places`); for ones that have been,
use the `cxprep` framework.

[Toasty Pipeline]: https://toasty.readthedocs.io/en/latest/pipeline.html

To prepare to run the pipeline, do the following:

1. Make sure that you've downloaded the AstroPix database, as describe in
   [Approach: AstroPix](#approach-astropix).
2. Change to a sub-directory in the `feeds` directory, e.g., `feeds/hst`.
3. Ensure that a `corepipe-storage.yaml` file exists there. This has the same
   format as the `toasty-store-config.yaml` file created by the [`toasty
   pipeline init`] command — you can just copy an existing file from the Toasty
   framework into this one.
4. Possibly run the `pipeline backfill` command, described below, to backfill
   data from the Toasty pipeline framework.

Once you're prepared, the pipeline steps are as follows:

- The `../../pipeline.py refresh` command downloads information about images that
  could be processed.
- The `../../pipeline.py fetch <IDS...>` command selects specific images for
  processing, downloading their data.
- The `../../pipeline.py process-todos` command tiles all images that have been
  fetched, and inserts their information into the `prep.txt` information file
  associated with the feed.
- At this point, you can review tiled images and edit their metadata in the
  `prep.txt` file. When an image is ready to publish, remove the `wip: yes`
  statement from its record in the `prep.txt` file.
- The `../../pipeline.py upload` processes all images that have been marked as
  ready (not `wip`) in the `prep.txt` file. It updates the WTML files based on
  any edits to `prep.txt`; uploads the associated data to the cloud; register
  the images with Constellations *in the unpublished state*; and also adds them
  to the `imagesets` and `places` databases. After uploading, you should `git
  commit` the local database updates and push your changes.
- Finally, for all new scenes that are uploaded to Constellations, you should
  review their display in the Constellations UI and mark them as "Published" to
  make them publicly visible once they’re ready.

[`toasty pipeline init`]: https://toasty.readthedocs.io/en/latest/cli/pipeline-init.html


### `pipeline backfill <WTML-FILE>`

This command is intended to help backfill data into this ingest pipeline from
a preexisting setup for the [Toasty Pipeline].

The argument should be a single merged WTML file that contains information about
*all* of the images currently being worked on as part of a Toasty Pipeline
session. This could be generated with something like [`wwtdatatool wtml merge`].

This command will process that file and use it to generate the `prep.txt` file
that drives the publication process. The unique IDs of the images are inferred
from the thumbnail image URL associated with each imageset.

[`wwtdatatool wtml merge`]: https://wwt-data-formats.readthedocs.io/en/latest/cli/wtml-merge.html

Once you have done this, you need to copy the Toasty Pipeline `processed` and/or
`uploaded` directories into the relevant feed directory here. The format of the
files in those directories is identical to the Toasty Pipeline framework.


## See also

The [`wwt-hips-list-importer`][hips] repo contains a script for generating the
`hips.wtml` catalog.

[hips]: https://github.com/WorldWideTelescope/wwt-hips-list-importer
