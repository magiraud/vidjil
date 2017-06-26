import json, argparse
import logging
import sys

class MigrateLogger():

    def __init__(self, level=logging.INFO):
        log = logging.getLogger('vidjil_migrate')
        log.setLevel(level)
        log.propagate = False
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(levelname)s\t- %(message)s')
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        log.addHandler(ch)
        self.log = log

    def info(self, text):
       self.log.info(text)

    def debug(self, text):
        self.log.debug(text)

    def error(self, text):
        self.log.error(text)

    def getLogger(self):
        return self.log

log = MigrateLogger()

def get_dict_from_row(row):
    '''
    Create a dict element from a Row element
    while filtering out some key pydal helper fields
    '''
    ex_fields = ['id', 'analysis_file', 'results_file', 'fused_file',
            'sequence_file', 'sample_set_membership', 'delete_record',
            'update_record']
    my_dict = {}
    for key in row.keys():
        if key not in ex_fields:
            tmp = row[key]
            if isinstance(tmp, datetime.datetime):
                tmp = tmp.__str__()
            my_dict[key] = tmp
    return my_dict

def reencode_dict(data):
    '''
    Recursively reencode the values and keys of a dict to utf-8.
    Takes a dict loaded from json, assumes all keys are strings.
    Values may be any type, only unicode values are reencoded
    '''
    if type(data) == dict:
        tmp = {}
        for key in data:
            val = data[key]
            tmp[key.encode('utf-8')] = reencode_dict(val)
        return tmp
    elif type(data) == unicode:
        return data.encode('utf-8')
    else:
        return data 

class Extractor():

    def __init__(self, db, level=logging.INFO):
        log.info("initialising extractor")
        self.db = db

    def populateSets(self, rows):
        log.debug("populate sets")
        sets = {}
        sample_set_ids = []
        for row in rows:
            log.debug("populating : %d, sample_set: %d" % (row.id, row.sample_set_id))
            sets[row.id] = get_dict_from_row(row)
            sample_set_ids.append(row.sample_set_id)
        return sets, sample_set_ids

    def getSequenceFiles(self, sample_set_ids):
        db = self.db
        rows = db((db.sample_set_membership.sample_set_id.belongs(sample_set_ids))
                & (db.sequence_file.id == db.sample_set_membership.sequence_file_id)
               ).select(db.sample_set_membership.ALL, db.sequence_file.ALL)
        return rows

    def populateSequenceFiles(self, rows):
        log.debug("populate sequence_files")
        memberships = {}
        sequence_files = {}
        for row in rows:
            ssm_id = row.sample_set_membership.id
            sf_id = row.sequence_file.id
            log.debug("populating sequence file: %d, membership: %d" % (sf_id, ssm_id))
            memberships[ssm_id] = get_dict_from_row(row.sample_set_membership)
            sequence_files[sf_id] = get_dict_from_row(row.sequence_file)
        return sequence_files, memberships

    def getTableEntries(self, table, ref_field, values):
        db = self.db
        rows = db(db[table][ref_field].belongs(values)).select(db[table].ALL)
        return rows

    def populateEntries(self, rows, etype=''):
        log.debug("populate %ss" % etype)
        data = {}
        for row in rows:
            my_dict = get_dict_from_row(row)
            log.debug("populating entry: %s" % str(my_dict))
            data[row.id] = my_dict
        return data

class GroupExtractor(Extractor):

    def __init__(self, db, level=logging.INFO):
        Extractor.__init__(self, db, level)

    def getAccessible(self, table, groupid):
        rows = db((db[table].id == db.auth_permission.record_id)
                & (db.auth_permission.table_name == table)
                & (db.auth_permission.name == PermissionEnum.access.value)
                & (db.auth_permission.group_id == groupid)
               ).select(db[table].ALL)
        return rows

class SampleSetExtractor(Extractor):

    def __init__(self, db, level=logging.INFO):
        Extractor.__init__(self, db, level)

    def getAccessible(self, table, ids):
        rows = db(db[table].id.belongs(ids)).select(db[table].ALL)
        return rows

class Importer():

    def __init__(self, groupid, db, level=logging.INFO):
        log.info("initialising importer")
        self.groupid = groupid
        self.db = db
        self.mappings = {}
        self.mappings['sample_set'] = {}
        self.mappings['sequence_file'] = {}

    def importSampleSets(self, stype, sets):
        log.debug("import sets")
        for sid in sets:
            log.debug("Importing set: %s" % sid)
            sset = sets[sid]
            ssid = db.sample_set.insert(sample_type = stype)
            log.debug("New sample_set %d" % ssid)
            self.mappings['sample_set'][sset['sample_set_id']] = ssid
            log.debug("Mapped: %d to %d" % (sset['sample_set_id'], ssid))
            sset['sample_set_id'] = ssid
            nid = db[stype].insert(**sset)
            log.debug("New %s: %d" % (stype, nid))
            db.auth_permission.insert(group_id=self.groupid,
                                      name=PermissionEnum.access.value,
                                      table_name=stype,
                                      record_id=nid)
            log.debug("associated set %d to group %d" % (nid, self.groupid))

    def importSequenceFiles(self, sequence_files):
        log.debug("import sequence_files")
        for sid in sequence_files:
            log.debug("importing sequence file: %s" % sid)
            seqf = sequence_files[sid]
            seqfid = db.sequence_file.insert(**seqf)
            log.debug("new sequence file: %d" % seqfid)
            self.mappings['sequence_file'][long(sid)] = seqfid
            log.debug("mapped: %d to %d" % (long(sid), seqfid))

    def importTable(self, table, ref_fields, values):
        log.debug("import %ss" % table)
        for vid in values:
            log.debug("importing %s: %s" % (table, vid))
            val = values[vid]
            for ref in ref_fields:
                ref_key = "%s_id" % ref
                log.debug("replacing %s: %d with %d" % (ref_key, val[ref_key], self.mappings[ref][val[ref_key]]))
                val[ref_key] = self.mappings[ref][val[ref_key]]
            oid = db[table].insert(**val)
            log.debug("new %s: %d" % (table, oid))

def export_peripheral_data(extractor, data_dict, sample_set_ids):
    sequence_rows = extractor.getSequenceFiles(sample_set_ids)
    data_dict['sequence_files'], data_dict['memberships'] = extractor.populateSequenceFiles(sequence_rows)

    results_rows = extractor.getTableEntries('results_file', 'sequence_file_id', data_dict['sequence_files'].keys())
    data_dict['results_files'] = extractor.populateEntries(results_rows, 'results_file')

    analysis_rows = extractor.getTableEntries('analysis_file', 'sample_set_id', sample_set_ids)
    data_dict['analysis_files'] = extractor.populateEntries(analysis_rows, 'analysis_file')

    fused_rows = extractor.getTableEntries('fused_file', 'sample_set_id', sample_set_ids)
    data_dict['fused_files'] = extractor.populateEntries(fused_rows, 'fused_file')

    return data_dict

def export_group_data(filename, groupid):
    log.info("exporting group data")
    ext = GroupExtractor(db)

    tables = {}

    patient_rows = ext.getAccessible('patient', groupid)
    tables['patients'], patient_ssids = ext.populateSets(patient_rows)

    run_rows = ext.getAccessible('run', groupid)
    tables['runs'], run_ssids = ext.populateSets(run_rows)

    generic_rows = ext.getAccessible('generic', groupid)
    tables['generics'], generic_ssids = ext.populateSets(generic_rows)
    
    sample_set_ids = patient_ssids + run_ssids + generic_ssids

    tables = export_peripheral_data(ext, tables, sample_set_ids)

    with open(filename, 'w') as outfile:
        json.dump(tables, outfile, ensure_ascii=False, encoding='utf-8')
    log.info("done")

def export_sample_set_data(filename, sample_type, sample_ids):
    log.info("exporting sample set data")
    ext = SampleSetExtractor(db)

    tables = {}

    rows = ext.getAccessible(sample_type, sample_ids)
    key = "%ss" % sample_type
    tables[key], sample_set_ids = ext.populateSets(rows)

    tables = export_peripheral_data(ext, tables, sample_set_ids)

    with open(filename, 'w') as outfile:
        json.dump(tables, outfile, ensure_ascii=False, encoding='utf-8')
    log.info("done")

def import_data(filename, groupid, dry_run=False):
    log.info("importing data")
    data = {}
    with open(filename, 'r') as infile:
        tmp = json.load(infile, encoding='utf-8')
        data = reencode_dict(tmp)

    imp = Importer(groupid, db, logging.INFO)

    try:
        set_types = ['patient', 'run', 'generic']
        for stype in set_types:
            key = "%ss" % stype
            if key in data:
                imp.importSampleSets(stype, data[key])

        imp.importSequenceFiles(data['sequence_files'])

        imp.importTable('sample_set_membership', ['sample_set', 'sequence_file'], data['memberships'])
        imp.importTable('results_file', ['sample_set'], data['results_files'])
        imp.importTable('analysis_file', ['sample_set'], data['analysis_files'])
        imp.importTable('fused_file', ['sample_set'], data['fused_files'])

        if dry_run:
            db.rollback()
            log.info("dry run successful, no data saved")
        else:
            db.commit()
            log.info("done")
    except:
        log.error("something went wrong, rolling back")
        db.rollback()
        log.error("rollback was successful")
        raise

def main():
    parser = argparse.ArgumentParser(description='Export and import data')
    subparsers = parser.add_subparsers(help="Select operation mode", dest='command')

    exp_parser = subparsers.add_parser('export', help='Export data from the DB into a JSON file')
    exp_subparser = exp_parser.add_subparsers(dest='mode', help='Select data selection method')

    ss_parser = exp_subparser.add_parser('sample_set', help='Export data by sample-set ids')
    ss_parser.add_argument('sample_type', type=str, choices=['patient', 'run', 'generic'], help='Type of sample')
    ss_parser.add_argument('ssids', metavar='ID', type=long, nargs='+', help='Ids of sample sets to be extracted')

    group_parser = exp_subparser.add_parser('group', help='Extract data by groupid')
    group_parser.add_argument('groupid', type=long, help='The long ID of the group')

    import_parser = subparsers.add_parser('import', help='Import data from JSON into the DB')
    import_parser.add_argument('--dry-run', dest='dry', action='store_true', help='With a dry run, the data will not be saved to the database')
    import_parser.add_argument('groupid', type=long, help='The long ID of the group')

    parser.add_argument('-f', type=str, dest='filename', default='./export.txt', help='Select the file to be read or written to')
    parser.add_argument('--debug', dest='debug', action='store_true', help='Output debug information')

    args = parser.parse_args()

    if args.command == 'export':
        if args.mode == 'group':
            export_group_data(args.filename, args.groupid)
        elif args.mode == 'sample_set':
            export_sample_set_data(args.filename, args.sample_type, args.ssids)
    elif args.command == 'import':
        if args.dry:
            log.log.setLevel(logging.DEBUG)
        import_data(args.filename, args.groupid, args.dry)

if __name__ == '__main__':
    main()
