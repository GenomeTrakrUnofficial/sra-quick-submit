sra-quick-submit
================

Quick Python tool for making SRA submissions as part of the GenomeTrakr Next Generation Sequencing Network for Food Pathogen Traceability project.


	usage: sra_quick_submit [-h] [-o PATH] [-d YYYY-MM-DD] [-l CHARACTER]
                        	[-n NAME] [-e email@email.email]
                        	<PRJNAxxxxxxx> <PATH | FILE>

		SRA Quick Submit
	Aug 16, Justin Payne 
	ORISE FDA-CFSAN-ORS-DM-MMSB
	justin.payne@fda.hhs.gov
	v1.6b

	positional arguments:
	  <PRJNAxxxxxxx>
	  <PATH | FILE>

	optional arguments:
	  -h, --help            show this help message and exit
	  -o PATH, --output PATH
							Output directory. Will be created if it doesn't
							already exist. [default:$PWD]
	  -d YYYY-MM-DD, --hold-date YYYY-MM-DD
							Hold this submission until specified date. SRA allows
							up to a one-year hold.
	  -l CHARACTER, --delimiter CHARACTER
							Character used as delimiter in table. [default: \t]
	  -n NAME, --name NAME  Submitter name.
	  -e email@email.email, --email email@email.email
							Submitter email.
	  -m INT, --library-length INT
							Nominal library insert length [default: 500]
	  -r INT, --read-length INT
							Total read length (number of primary flows) [default:
							250]
	  -g <sample name | 'all'>, --merge <sample name | 'all'>
							Merge identical sample names into single experiment.
							This should be done if the same library was re-used
							for multiple runs. Specify the sample names to merge
							or "all" to merge all multiply-present samples
							[default: do not merge]
	  --make-table          Instead of producing a submission, produce a table
							template which this script can accept as input.

	
Import a table file of metadata or a MiSeq output directory and generate 
submittable XML tarballs that can be uploaded to NCBI SRA. Accepts any line
ending (Mac, PC, Linux).


	Change history:
	Aug 29 v1.1b: protection from sample name collision. 
	Sep 6  v1.2b: -p flag for specifying BioProject ID.
	Sep 16 v1.5b:  release version for GenomeTrakr community.
	Sep 16 v1.5b: release version for GenomeTrakr community.
	Sep 27 v1.6b: -g flag to merge runs with existing experiments, if possible 


Usage example:

	$ sra_quick_submit PRJNA00000000 /path/to/a/miseq/output/folder/130730_M01836_0006_000000000-A3N78/ -o /another/path/
