#!/usr/bin/env python

import datetime
import csv
import tarfile
import os
import sys
from os.path import *
import xml.etree.ElementTree as xml
import subprocess
import urllib

description = r"""
	SRA Quick Submit
	Aug 16, Justin Payne 
	ORISE FDA-CFSAN-ORS-DM-MMSB
	justin.payne@fda.hhs.gov
	v1.6b
	
Import a table file of metadata or a MiSeq output directory and generate 
submittable XML tarballs that can be uploaded to NCBI SRA. Accepts any line
ending (Mac, PC, Linux)."""

change_history = """
Change history:
Aug 29 v1.1b: protection from sample name collision. 
Sep 6  v1.2b: -p flag for specifying BioProject ID.
Sep 16 v1.5b: release version for GenomeTrakr community.
Sep 27 v1.6b: -g flag to merge runs with existing experiments, if possible 
Feb 2, 2021 v1.7: Update to Python 3
"""



experiment = """
<EXPERIMENT alias="{Sample Name}{num}" xmlns="" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<TITLE>Whole genome shotgun sequencing of {organism} by Illumina MiSeq</TITLE>
	<STUDY_REF accession="{project}" />
	<DESIGN>
      <DESIGN_DESCRIPTION>MiSeq deep shotgun sequencing of cultured isolate.</DESIGN_DESCRIPTION>
      <SAMPLE_DESCRIPTOR accession="{Biosample Accession}" />
      <LIBRARY_DESCRIPTOR>
        <LIBRARY_NAME>{organism} Nextera XT shotgun library</LIBRARY_NAME>
        <LIBRARY_STRATEGY>WGS</LIBRARY_STRATEGY>
        <LIBRARY_SOURCE>GENOMIC</LIBRARY_SOURCE>
        <LIBRARY_SELECTION>RANDOM</LIBRARY_SELECTION>
        <LIBRARY_LAYOUT>
          <PAIRED NOMINAL_LENGTH="{library_length}" />
        </LIBRARY_LAYOUT>
        <LIBRARY_CONSTRUCTION_PROTOCOL>Illumina Nextera XT library created for {organism}.</LIBRARY_CONSTRUCTION_PROTOCOL>
      </LIBRARY_DESCRIPTOR>
      <SPOT_DESCRIPTOR>
              <SPOT_DECODE_SPEC>
                <SPOT_LENGTH>{spot}</SPOT_LENGTH>
                <READ_SPEC>
                  <READ_INDEX>0</READ_INDEX>
                  <READ_CLASS>Application Read</READ_CLASS>
                  <READ_TYPE>Forward</READ_TYPE>
                  <BASE_COORD>1</BASE_COORD>
                </READ_SPEC>
                <READ_SPEC>
                  <READ_INDEX>1</READ_INDEX>
                  <READ_CLASS>Application Read</READ_CLASS>
                  <READ_TYPE>Reverse</READ_TYPE>
                  <BASE_COORD>{half_spot}</BASE_COORD>
                </READ_SPEC>
              </SPOT_DECODE_SPEC>
      </SPOT_DESCRIPTOR>
    </DESIGN>
	<PLATFORM>
		<ILLUMINA>
			<INSTRUMENT_MODEL>Illumina MiSeq</INSTRUMENT_MODEL>
		</ILLUMINA>
	</PLATFORM>
	<PROCESSING>
		<PIPELINE>
			<PIPE_SECTION section_name="base caller">
				<STEP_INDEX>0</STEP_INDEX>
			   	<PREV_STEP_INDEX>NULL</PREV_STEP_INDEX>
			   	<PROGRAM>RTA</PROGRAM>
			   	<VERSION>{version}</VERSION>
			</PIPE_SECTION>
		</PIPELINE>
	</PROCESSING>
</EXPERIMENT>
"""

run = """
<RUN alias="{Sample Name}{num}">
 <EXPERIMENT_REF refname="{Sample Name}" />
 <DATA_BLOCK>
  <FILES>
  	<FILE checksum_method="MD5" filetype="fastq" checksum="{file1_checksum}" filename="{file1_name}" />
  	<FILE checksum_method="MD5" filetype="fastq" checksum="{file2_checksum}" filename="{file2_name}" />
  </FILES>
 </DATA_BLOCK>
</RUN>
"""

submission = """
<SUBMISSION alias="{Sample Name}{num}" submission_comment="GenomeTrakr pathogen sampling project">	
	<CONTACTS>
		<CONTACT inform_on_error="mailto:{email}" inform_on_status="{email}" name="{name}" />
	</CONTACTS>
	<ACTIONS>
	<ACTION><ADD schema="experiment" source="{Sample Name}{num}.experiment.xml" /></ACTION>
	<ACTION><ADD schema="run" source="{Sample Name}{num}.run.xml" /></ACTION>
	<ACTION><HOLD HoldUntilDate="{date}Z" /></ACTION></ACTIONS>
</SUBMISSION>
"""

submission_no_exp = """
<SUBMISSION alias="{Sample Name}" submission_comment="GenomeTrakr pathogen sampling project">	
	<CONTACTS>
		<CONTACT inform_on_error="mailto:{email}" inform_on_status="{email}" name="{name}" />
	</CONTACTS>
	<ACTIONS>
	<ACTION><ADD schema="run" source="{Sample Name}.run.xml" /></ACTION>
	<ACTION><HOLD HoldUntilDate="{date}Z" /></ACTION></ACTIONS>
</SUBMISSION>
"""

sample_names = list()
sample_cache = dict()


class progressbar(object):
	"A basic CLI progress bar. From Python Cookbook 2nd Ed., Martelli, Ravenscroft, Ascher. 2005 O'Reilly Media."
	def __init__(self, finalcount, block_char='.', out=sys.stdout):
		self.finalcount = finalcount
		self.blockcount = 0
		self.block = block_char
		self.f = out
		if not self.finalcount: return
		self.f.write('\n------------------ % Progress -------------------1\n')
		self.f.write('    1    2    3    4    5    6    7    8    9    0\n')
		self.f.write('----0----0----0----0----0----0----0----0----0----0\n')
	def progress(self, count):
		count = min(count, self.finalcount)
		if self.finalcount:
			percentcomplete = int(round(100.0*count/self.finalcount))
			if percentcomplete < 1: percentcomplete = 1
		else:
			percentcomplete=100
		blockcount = int(percentcomplete//2)
		if blockcount <= self.blockcount:
			return
		for i in range(self.blockcount, blockcount):
			self.f.write(self.block)
		self.f.flush()
		self.blockcount = blockcount
		if percentcomplete == 100:
			self.f.write("\n")
		
def check_ncbi_for_prev_experiment(sample_name):
	"Use a combination of NCBI E-Utils to detect past MiSeq experiments for this sample, so that new runs can be attached"
	if "SAMN" not in sample_name:
		raise ValueError("{} not a valid NCBI BioSample ID.".format(sample_name))
	query = urllib.urlencode({"db":"sra", "term":sample_name, "field":"BSPL"})
	r1 = xml.fromstring(urllib.urlopen("http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", data=query).read())
	for sra in [e.text for e in r1.findall(".//Id")]:
		query = urllib.urlencode({"db":"SRA", "id":sra})
		r2 = xml.fromstring(urllib.urlopen("http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", data=query).read())
		for sra_exp in r2.findall(".//EXPERIMENT"):
			if "Illumina MiSeq" in sra_exp.find(".//INSTRUMENT_MODEL").text:
				return sra_exp.attrib['accession']
	return False

def make_submission(path, entry, project, hold, merge=False, **kwargs):
	"Produce three submission files - run, experiment, submission - and then tar them up."
	
	exp_acc = None

	entry.update(kwargs)
	if not exists(path):
		os.makedirs(path)
		print("Made {}.".format(path))
	
	if merge and (entry['Sample Name'] in merge.split(" ") or 'all' in merge):
		entry['num'] = ''
		if entry['Sample Name'] in sample_cache:
			r = xml.fromstring(run.format(**entry))
			run_set = sample_cache[entry['Sample Name']]
			run_set.append(r)
		else:
			sample_cache[entry['Sample Name']] = run_set = xml.Element("RUN_SET")
			run_set.append(xml.fromstring(run.format(**entry)))
		
		try:
			exp_acc = check_ncbi_for_prev_experiment(entry['Biosample Accession'])
		except ValueError:
			print(locals())
		
		if exp_acc:
			print("Found a previous experiment: {}".format(exp_acc))
			sub = xml.fromstring(submission_no_exp.format(date=hold, **entry))
			for ref in run_set.findall(".//EXPERIMENT_REF"):
				ref.attrib['accession'] = exp_acc
		else:
			print("No experiment found. Creating a new one...")
			exp = xml.fromstring(experiment.format(project=project, **entry))
			xml.ElementTree(exp).write(join(path, '{Sample Name}.experiment.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
			sub = xml.fromstring(submission.format(date=hold, **entry))
		
		xml.ElementTree(run_set).write(join(path, '{Sample Name}.run.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
		xml.ElementTree(sub).write(join(path, '{Sample Name}.submission.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
		with tarfile.open(join(path, '{Sample Name}.submission_archive.tar'.format(**entry)), 'w', format=tarfile.GNU_FORMAT) as tarball:
			tarball.add(join(path, '{Sample Name}.run.xml'.format(**entry)), arcname='{Sample Name}.run.xml'.format(**entry))
			tarball.add(join(path, '{Sample Name}.submission.xml'.format(**entry)), arcname='{Sample Name}.submission.xml'.format(**entry))
			try:
				tarball.add(join(path, '{Sample Name}.experiment.xml'.format(**entry)), arcname='{Sample Name}.experiment.xml'.format(**entry))
				print("Produced run, experiment, and submission files for {}".format(entry['Sample Name']))
			except (OSError, IOError):
				print("Produced run and submission files for {}".format(entry['Sample Name']))
				
		
		
	else:
		if entry['Sample Name'] in sample_names:
			entry['num'] = ".{:02}".format(sample_names.count(entry['Sample Name']) + 1)
		else:
			entry['num'] = ''
	
		try:
			
			exp = xml.fromstring(experiment.format(project=project, **entry))
			xml.ElementTree(exp).write(join(path, '{Sample Name}{num}.experiment.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
	
			r = xml.fromstring(run.format(**entry))
			r_set = xml.Element("RUN_SET")
			r_set.append(r)
			xml.ElementTree(r).write(join(path, '{Sample Name}{num}.run.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
	
			sub = xml.fromstring(submission.format(date=hold, **entry))
			xml.ElementTree(sub).write(join(path, '{Sample Name}{num}.submission.xml'.format(**entry)), encoding="UTF-8", xml_declaration=True)
		except xml.ParseError as e:
			print("XML internal parsing failed. Tried to parse:")
			print(experiment.format(project=project, **entry))
			print(run.format(**entry))
			print(submission.format(date=date, **entry))
			raise e
		tarball = tarfile.open(join(path, '{Sample Name}{num}.submission_archive.tar'.format(**entry)), 'w', format=tarfile.GNU_FORMAT)
		tarball.add(join(path, '{Sample Name}{num}.experiment.xml'.format(**entry)), arcname='{Sample Name}{num}.experiment.xml'.format(**entry))
		tarball.add(join(path, '{Sample Name}{num}.run.xml'.format(**entry)), arcname='{Sample Name}{num}.run.xml'.format(**entry))
		tarball.add(join(path, '{Sample Name}{num}.submission.xml'.format(**entry)), arcname='{Sample Name}{num}.submission.xml'.format(**entry))
		tarball.close()
		sample_names.append(entry['Sample Name'])
	
def process_miseq_output(input_dir, output_dir, project=False, progressbar=progressbar, **kwargs):
	import hashlib
	run_params = xml.parse(join(input_dir, 'RunParameters.xml'))
	version = run_params.find('.//RTAVersion').text
	with open(join(input_dir, 'SampleSheet.csv'), 'rU') as samplesheet:
		for line in samplesheet: #step past header lines to data section
			if '[Data]' in line:
				break
		entries = list(csv.DictReader(samplesheet, delimiter=','))
		for entry, index in zip(entries, range(1, len(entries) + 1)):
			if 'SAMN' in entry['Sample_Name']:
				entry['Sample Name'] = entry['organism'] = entry['Biosample Accession'] = entry['Sample_Name']
			elif 'SAMN' in entry['Sample_ID']:
				entry['Biosample Accession'] = entry['Sample_ID']
				entry['Sample Name'] = entry['organism'] = entry['Sample_Name']
			else:
				print("Can't submit sample {Sample_Name}, no NCBI BioSample ID.".format(**entry))
				break
			try:
				for file_no in (1, 2):
					f = join(input_dir, 'Data', 'Intensities', 
							'BaseCalls', '{sample}_S{index}_L001_R{file_no}_001.fastq.gz'.format(
								sample=entry['Sample_Name'].replace("_", "-"),
								index=index,
								file_no=file_no
							)
						)
					with open(f,'rb') as runfile:
						print("Hashing {}...".format(basename(f)))
						pbar = progressbar(os.stat(f).st_size / 1048576)
						hash = hashlib.md5()
						line_no = 0
						for block in iter(lambda:runfile.read(1048576), ''):
							hash.update(block)
							line_no += 1
							pbar.progress(line_no)
							
						entry['file{}_name'.format(file_no)] = '{sample}_S{index}_L001_R{file_no}_001.fasta.gz'.format(
							sample=entry['Sample_Name'],
							index=index,
							file_no=file_no
						)
						entry['file{}_checksum'.format(file_no)] = hash.hexdigest()
						entry['version'] = version
			except (IOError, OSError) as e:
				print(e)
				continue
			make_submission(output_dir, entry, project or entry['Sample_Project'], **kwargs)	
				
					
def output_table(path):
	if not exists(path):
		os.makedirs(path)
	with open(join(path, 'SRA_Quick_Submit_template.txt'), 'w') as template_file:
		for h in ('Sample Name',
				  'organism',
				  'strain',
				  'Biosample Accession',
				  'file1_name',
				  'file1_checksum',
				  'file2_name',
				  'file2_checksum'):
			template_file.write("{}\t".format(h))
		template_file.write("\n")
	print("Wrote {}/SRA_Quick_Submit_template.txt".format(path))
	
	

	
def main():
	import argparse
			
	p = argparse.ArgumentParser(description=description, 
								epilog=change_history, 
								argument_default=False,
								formatter_class=argparse.RawDescriptionHelpFormatter)						
	
	p.add_argument('-o', '--output', action='store', 
				   metavar='PATH', 
				   help="Output directory. Will be created if it doesn't already exist. [default: %(default)s]", 
				   default=os.getcwd())
	p.add_argument('-d', '--hold-date', metavar="YYYY-MM-DD", 
				   help="Hold this submission until specified date. SRA allows up to a one-year hold.",
				   action='store',
				   dest='hold')
	p.add_argument('-l', '--delimiter', metavar="CHARACTER", 
				   help="Character used as delimiter in table. [default: \\t]", 
				   action='store', 
				   default='\t')
	p.add_argument('-n', '--name', metavar="NAME", help="Submitter name.", action='store')
	p.add_argument('-e', '--email', metavar="email@email.email", help="Submitter email.", action='store')
	p.add_argument('-m', '--library-length', metavar="INT", 
				   help='Nominal library insert length [default: 500]', 
				   action='store', 
				   default=500)
	

	p.add_argument('-r', '--read-length', metavar="INT", 
				   help='Total read length (number of primary flows) [default: 250]', 
				   action='store', 
				   default=0,
				   type=int)
	p.add_argument('-g', '--merge', metavar="<sample name | 'all'>",
				   help='Merge identical sample names into single experiment. This should be done if the same library was re-used for multiple runs. Specify the sample names to merge or "all" to merge all multiply-present samples [default: do not merge]',
				   action='store',
				   default=False)
	p.add_argument('project', metavar="<PRJNAxxxxxxx>", action='store')
	p.add_argument('input', metavar="<PATH | FILE>", action='store')
	p.add_argument('--make-table', help="Instead of producing a submission, produce a table template which this script can accept as input.", action='store_true')
	
	#quickly manually parse sys.argv, looking for the 'write table' option
	if '--make-table' in sys.argv:
		try:
			path = sys.argv.pop(sys.argv.index("-o") + 1)
		except ValueError:
			try:
				path = sys.argv.pop(sys.argv.index("--output") + 1)
			except ValueError:
				path = os.getcwd()
		output_table(path)
		quit()
	
	#allow argparse to parse the command-line args
	args = p.parse_args()
	
	if not args.hold:
		args.hold = datetime.datetime.today().strftime("%Y-%m-%d")
		print("No HOLD date specified, using default: {}".format(args.hold))
		
	if not args.name:
		for key in ('USER', 'LOGNAME'):
			try:
				args.name = os.environ[key]
				print("Name not specified; got '{}' from shell environment".format(args.name))
				break
			except KeyError:
				pass
		if not args.name:
			print("""No name given and $USER/$LOGNAME vars not set. Specify submitter name with -n "My Name".""")
			quit()
			
	if not args.email:
		try:
			args.email = os.environ['USER_PRINCIPAL_NAME']
			print("Email not specified; got '{}' from shell environment".format(args.email))
		except KeyError:
			print("No email given and $USER_PRINCIPAL_NAME var not set. Specify submitter email with -e email@email.email")
			quit()
			
	if not args.read_length:
		args.spot = 502
		args.half_spot = 251	
	else:
		args.half_spot = args.read_length + 1
		args.spot = (args.read_length + 1) * 2
	
	if isdir(args.input):
		process_miseq_output(abspath(args.input), abspath(args.output), **vars(args))
	else:		
		try:
			with open(abspath(args.input), 'rU') as input_file:
				entries = csv.DictReader(input_file, dialect='excel', delimiter=args.delimiter)
				for entry in entries:
					make_submission(abspath(args.output), entry, version='1.17', **vars(args))
		except IndexError:
			print("No metadata file specified.")
			print(usage)
			quit()
		except IOError:
			print("{} not found. Check file location and try again.".format(sys.argv[1]))
			quit()
		
	
	

if __name__ == '__main__':
	main()