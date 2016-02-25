# coding: utf8
import os
import defs
import re
import os.path
import time
import sys
import datetime
import random
import xmlrpclib


def assert_scheduler_task_does_not_exist(args):
    ##check scheduled run
    row = db( ( db.scheduler_task.args == args)
         & ( db.scheduler_task.status != "FAILED"  )
         & ( db.scheduler_task.status != "EXPIRED"  )
         & ( db.scheduler_task.status != "TIMEOUT"  )
         & ( db.scheduler_task.status != "COMPLETED"  )
         ).select()

    if len(row) > 0 :
        res = {"message": "task already registered"}
        return res

    return None


def schedule_run(id_sequence, id_sample_set, id_config, grep_reads=None):
    from subprocess import Popen, PIPE, STDOUT, os

    #check results_file
    row = db( ( db.results_file.config_id == id_config ) & 
             ( db.results_file.sequence_file_id == id_sequence )  
             ).select()
    
    ts = time.time()
    data_id = db.results_file.insert(sequence_file_id = id_sequence,
                                     run_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                     config_id = id_config )
        
    if grep_reads:
        args = [id_sequence, id_config, data_id, None, grep_reads]
    else:
        ## check fused_file
        row2 = db( ( db.fused_file.config_id == id_config ) &
                   ( db.fused_file.sample_set_id == id_sample_set )
               ).select()

        if len(row2) > 0 : ## update
            fuse_id = row2[0].id
        else:             ## create
            fuse_id = db.fused_file.insert(sample_set_id = id_sample_set,
                                           config_id = id_config)

        args = [id_sequence, id_config, data_id, fuse_id, None]

    err = assert_scheduler_task_does_not_exist(str(args))
    if err:
        log.error(err)
        return err

    program = db.config[id_config].program
    ##add task to scheduler
    task = scheduler.queue_task(program, args,
                                repeats = 1, timeout = defs.TASK_TIMEOUT)
    db.results_file[data_id] = dict(scheduler_task_id = task.id)

    filename= db.sequence_file[id_sequence].filename

    res = {"redirect": "reload",
           "message": "[%s] (%s) c%s: process requested - %s %s" % (data_id, id_sample_set, id_config, grep_reads, filename)}

    log.info(res)
    return res


def run_vidjil(id_file, id_config, id_data, id_fuse, grep_reads,
               clean_before=False, clean_after=False):
    from subprocess import Popen, PIPE, STDOUT, os
    
    ## les chemins d'acces a vidjil / aux fichiers de sequences
    germline_folder = defs.DIR_VIDJIL + '/germline/'
    upload_folder = defs.DIR_SEQUENCES
    out_folder = defs.DIR_OUT_VIDJIL_ID % id_data
    
    cmd = "rm -rf "+out_folder 
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    
    ## filepath du fichier de séquence
    row = db(db.sequence_file.id==id_file).select()
    filename = row[0].data_file
    output_filename = defs.BASENAME_OUT_VIDJIL_ID % id_data
    seq_file = upload_folder+filename

    ## config de vidjil
    vidjil_cmd = db.config[id_config].command
    vidjil_cmd = vidjil_cmd.replace( ' germline' ,germline_folder)

    if grep_reads:
        # TODO: security, assert grep_reads XXXX
        vidjil_cmd += ' -FaW "%s" ' % grep_reads
    
    os.makedirs(out_folder)
    out_log = out_folder+'/'+output_filename+'.vidjil.log'
    vidjil_log_file = open(out_log, 'w')

    ## commande complete
    cmd = defs.DIR_VIDJIL + '/vidjil ' + ' -o  ' + out_folder + " -b " + output_filename
    cmd += ' ' + vidjil_cmd + ' '+ seq_file
    
    ## execute la commande vidjil
    print "=== Launching Vidjil ==="
    print cmd    
    print "========================"
    sys.stdout.flush()

    p = Popen(cmd, shell=True, stdin=PIPE, stdout=vidjil_log_file, stderr=STDOUT, close_fds=True)

    (stdoutdata, stderrdata) = p.communicate()

    print "Output log in "+out_folder+'/'+output_filename+'.vidjil.log'
    sys.stdout.flush()
    db.commit()

    ## Get result file
    if grep_reads:
        out_results = out_folder + '/seq/clone.fa-1'
    else:
        out_results = out_folder + '/' + output_filename + '.vidjil'

    print "===>", out_results
    results_filepath = os.path.abspath(out_results)

    try:
        stream = open(results_filepath, 'rb')
    except IOError:
        print "!!! Vidjil failed, no result file"
        res = {"message": "[%s] c%s: Vidjil FAILED - %s" % (id_data, id_config, out_folder)}
        log.error(res)
        raise IOError
    
    ## Parse some info in .log
    vidjil_log_file.close()

    segmented = re.compile("==> segmented (\d+) reads \((\d*\.\d+|\d+)%\)")
    windows = re.compile("==> found (\d+) .*-windows in .* segments .* inside (\d+) sequences")
    info = ''
    reads = None
    segs = None
    ratio = None
    wins = None
    for l in open(out_log):
        m = segmented.search(l)
        if m:
            print l,
            segs = int(m.group(1))
            ratio = m.group(2)
            info = "%d segmented (%s%%)" % (segs, ratio)
            continue
        m = windows.search(l)
        if m:
            print l,
            wins = int(m.group(1))
            reads = int(m.group(2))
            info = "%d reads, " % reads + info + ", %d windows" % wins
            break


    ## insertion dans la base de donnée
    ts = time.time()
    
    db.results_file[id_data] = dict(status = "ready",
                                 run_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                 data_file = stream
                                )
    
    db.commit()
    
    if clean_after:
        clean_cmd = "rm -rf " + out_folder 
        p = Popen(clean_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
    
    ## l'output de Vidjil est stocké comme resultat pour l'ordonnanceur
    ## TODO parse result success/fail

    config_name = db.config[id_config].name

    res = {"message": "[%s] c%s: Vidjil finished - %s - %s" % (id_data, id_config, info, out_folder)}
    log.info(res)


    if not grep_reads:
        for row in db(db.sample_set_membership.sequence_file_id==id_file).select() :
	    sample_set_id = row.sample_set_id
	    print row.sample_set_id
            run_fuse(id_file, id_config, id_data, id_fuse, sample_set_id, clean_before = False)

    return "SUCCESS"

def run_mixcr(id_file, id_config, id_data, id_fuse, clean_before=False, clean_after=False):
    from subprocess import Popen, PIPE, STDOUT, os
    import time

    upload_folder = defs.DIR_SEQUENCES
    out_folder = defs.DIR_OUT_VIDJIL_ID % id_data

    cmd = "rm -rf "+out_folder
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()

    ## filepath du fichier de séquence
    row = db(db.sequence_file.id==id_file).select()
    filename = row[0].data_file
    output_filename = defs.BASENAME_OUT_VIDJIL_ID % id_data
    seq_file = upload_folder+filename

    ## config de vidjil
    arg_cmd = db.config[id_config].command

    os.makedirs(out_folder)
    out_log = out_folder + output_filename+'.mixcr.log'
    log_file = open(out_log, 'w')

    out_alignments = out_folder + output_filename + '.align.vdjca'
    out_clones =  out_folder + output_filename + '.clones.clns'
    out_results = out_folder + output_filename + '.mixcr'

    ## commande complete
    mixcr = defs.DIR_MIXCR + 'mixcr'
    cmd = mixcr + ' align --save-reads -t 1'
    #+ output_filename
    cmd += ' ' + seq_file  + ' ' + out_alignments
    cmd += ' && ' + mixcr + ' assemble -t 1 ' + out_alignments + ' ' + out_clones
    cmd += ' && ' + mixcr + ' exportClones -t 1 ' + arg_cmd + ' ' + out_clones + ' ' + out_results

    ## execute la commande MiXCR
    print "=== Launching MiXCR ==="
    print cmd
    print "========================"
    sys.stdout.flush()

    p = Popen(cmd, shell=True, stdin=PIPE, stdout=log_file, stderr=STDOUT, close_fds=True)
    p.wait()

    print "Output log in " + out_log
    sys.stdout.flush()

    ## Get result file
    print "===>", out_results
    alignments_filepath = os.path.abspath(out_alignments)


    results_filepath = os.path.abspath(out_results)
    try:
        stream = open(results_filepath, 'rb')
    except IOError:
        print "!!! MiXCR failed, no result file"
        res = {"message": "[%s] c%s: MiXCR FAILED - %s" % (id_data, id_config, out_folder)}
        log.error(res)
        raise IOError

    ## insertion dans la base de donnée
    ts = time.time()
    
    db.results_file[id_data] = dict(status = "ready",
                                 run_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                 data_file = stream
                                )
    
    db.commit()

    config_name = db.config[id_config].name
    res = {"message": "[%s] c%s: MiXCR finished - %s" % (id_data, id_config, out_folder)}
    log.info(res)

    for row in db(db.sample_set_membership.sequence_file_id==id_file).select() :
        sample_set_id = row.sample_set_id
        print row.sample_set_id
        run_fuse(id_file, id_config, id_data, id_fuse, sample_set_id, clean_before = False)


    return "SUCCESS"

def run_copy(id_file, id_config, id_data, id_fuse, clean_before=False, clean_after=False):
    from subprocess import Popen, PIPE, STDOUT, os
    
    ## les chemins d'acces a vidjil / aux fichiers de sequences
    upload_folder = defs.DIR_SEQUENCES
    output_filename = defs.BASENAME_OUT_VIDJIL_ID % id_data
    out_folder = defs.DIR_OUT_VIDJIL_ID % id_data
    
    cmd = "rm -rf "+out_folder 
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    
    ## filepath du fichier de séquence
    row = db(db.sequence_file.id==id_file).select()
    filename = row[0].data_file
    
    os.makedirs(out_folder)
    vidjil_log_file = open(out_folder+'/'+output_filename+'.vidjil.log', 'w')

    print "Output log in "+out_folder+'/'+output_filename+'.vidjil.log'
    sys.stdout.flush()
    db.commit()
    
    ## récupération du fichier 
    results_filepath = os.path.abspath(defs.DIR_SEQUENCES+row[0].data_file)

    try:
        stream = open(results_filepath, 'rb')
    except IOError:
        print "!!! 'copy' failed, no file"
        res = {"message": "[%s] c%s: 'copy' FAILED - %s - %s" % (id_data, id_config, info, out_folder)}
        log.error(res)
        raise IOError
    
    ## insertion dans la base de donnée
    ts = time.time()
    
    db.results_file[id_data] = dict(status = "ready",
                                 run_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                 #data_file = row[0].data_file
                                 data_file = stream
                                )
    db.commit()
    
    if clean_after:
        clean_cmd = "rm -rf " + out_folder 
        p = Popen(clean_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
    
    ## l'output de Vidjil est stocké comme resultat pour l'ordonnanceur
    ## TODO parse result success/fail

    res = {"message": "[%s] c%s: 'copy' finished - %s" % (id_data, id_config, filename)}
    log.info(res)

    for row in db(db.sample_set_membership.sequence_file_id==id_file).select() :
        sample_set_id = row.sample_set_id
        print row.sample_set_id
        run_fuse(id_file, id_config, id_data, id_fuse, sample_set_id, clean_before = False)


    return "SUCCESS"



def run_fuse(id_file, id_config, id_data, id_fuse, sample_set_id, clean_before=True, clean_after=False):
    from subprocess import Popen, PIPE, STDOUT, os
    
    out_folder = defs.DIR_OUT_VIDJIL_ID % id_data
    output_filename = defs.BASENAME_OUT_VIDJIL_ID % id_data
    
    if clean_before:
        cmd = "rm -rf "+out_folder 
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
        os.makedirs(out_folder)    
    
    
    fuse_log_file = open(out_folder+'/'+output_filename+'.fuse.log', 'w')
    
    ## fuse.py 
    output_file = out_folder+'/'+output_filename+'.fused'
    files = ""
    sequence_file_list = ""
    query2 = db( ( db.results_file.sequence_file_id == db.sequence_file.id )
                   & ( db.sample_set_membership.sequence_file_id == db.sequence_file.id)
                   & ( db.sample_set_membership.sample_set_id == sample_set_id)
                   & ( db.results_file.config_id == id_config )
                   ).select( orderby=db.sequence_file.id|~db.results_file.run_date) 
    query = []
    sequence_file_id = 0
    for row in query2 : 
        if row.sequence_file.id != sequence_file_id :
            query.append(row)
            sequence_file_id = row.sequence_file.id
            
    for row in query :
        if row.results_file.data_file is not None :
            files += defs.DIR_RESULTS + row.results_file.data_file + " "
            sequence_file_list += str(row.results_file.sequence_file_id) + "_"
            
    fuse_cmd = db.config[id_config].fuse_command
    cmd = "python "+defs.DIR_FUSE+"/fuse.py -o "+ output_file + " " + fuse_cmd + " " + files


    print "=== fuse.py ==="
    print cmd
    print "==============="
    sys.stdout.flush()

    p = Popen(cmd, shell=True, stdin=PIPE, stdout=fuse_log_file, stderr=STDOUT, close_fds=True)
    (stdoutdata, stderrdata) = p.communicate()
    print "Output log in "+out_folder+'/'+output_filename+'.fuse.log'

    fuse_filepath = os.path.abspath(output_file)

    try:
        stream = open(fuse_filepath, 'rb')
    except IOError:
        print "!!! Fuse failed, no .fused file"
        res = {"message": "[%s] c%s: 'fuse' FAILED - %s" % (id_data, id_config, output_file)}
        log.error(res)
        raise IOError

    ts = time.time()
    db.fused_file[id_fuse] = dict(fuse_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                                 fused_file = stream,
                                 sequence_file_list = sequence_file_list)
    db.commit()

    if clean_after:
        clean_cmd = "rm -rf " + out_folder 
        p = Popen(clean_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
    
    res = {"message": "[%s] c%s: 'fuse' finished - %s" % (id_data, id_config, output_file)}
    log.info(res)

    return "SUCCESS"

def custom_fuse(file_list):
    from subprocess import Popen, PIPE, STDOUT, os

    if defs.PORT_FUSE_SERVER is None:
        raise IOError('This server cannot fuse custom data')
    random_id = random.randint(99999999,99999999999)
    out_folder = os.path.abspath(defs.DIR_OUT_VIDJIL_ID % random_id)
    output_filename = defs.BASENAME_OUT_VIDJIL_ID % random_id
    
    cmd = "rm -rf "+out_folder 
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    os.makedirs(out_folder)    

    res = {"message": "'custom fuse' (%d files): %s" % (len(file_list), ','.join(file_list))}
    log.info(res)
        
    ## fuse.py 
    output_file = out_folder+'/'+output_filename+'.fused'
    files = ""
    for id in file_list :
        if db.results_file[id].data_file is not None :
            files += os.path.abspath(defs.DIR_RESULTS + db.results_file[id].data_file) + " "
    
    cmd = "python "+ os.path.abspath(defs.DIR_FUSE) +"/fuse.py -o "+output_file+" -t 100 "+files
    proc_srvr = xmlrpclib.ServerProxy("http://localhost:%d" % defs.PORT_FUSE_SERVER)
    fuse_filepath = proc_srvr.fuse(cmd, out_folder, output_filename)
    
    try:
        f = open(fuse_filepath, 'rb')
        data = gluon.contrib.simplejson.loads(f.read())
    except IOError, e:
        res = {"message": "'custom fuse' -> IOError"}
        log.error(res)
        raise e

    clean_cmd = "rm -rf " + out_folder 
    p = Popen(clean_cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()

    res = {"message": "'custom fuse' -> finished"}
    log.info(res)

    return data

from gluon.scheduler import Scheduler
scheduler = Scheduler(db, dict(vidjil=run_vidjil,
                               mixcr=run_mixcr,
                               none=run_copy))
