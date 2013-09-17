sra-quick-submit
================

Quick Python tool for making SRA submissions as part of the GenomeTrakr Joint Foodborne Pathogen Sampling Project


	usage: sra_quick_submit [-h] [-o PATH] [-d YYYY-MM-DD] [-l CHARACTER]
                        	[-n NAME] [-e email@email.email]
                        	PRJNAxxxxxxx PATH or FILE

	SRA Quick Submit
	Aug 16, Justin Payne 
	ORISE FDA-CFSAN-ORS-DM-MMSB
	justin.payne@fda.hhs.gov
	v1.5b
	
Import a table file of metadata or a MiSeq output directory and generate 
submittable XML tarballs that can be uploaded to NCBI SRA. Accepts any line
ending (Mac, PC, Linux).


	Change history:
	Aug 29 v1.1b: protection from sample name collision. 
	Sep 6  v1.2b: -p flag for specifying BioProject ID.
	Sep 16 v1.5b:  release version for GenomeTrakr community.


Usage example:

	$ sra_quick_submit PRJNA00000000 /path/to/a/miseq/output/folder/130730_M01836_0006_000000000-A3N78/ -o /another/path/