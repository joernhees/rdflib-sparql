import collections

from rdflib import Graph, Namespace, RDF
from rdflib.query import Result

from rdflib_sparql.parser import parseQuery
from rdflib_sparql.processor import SPARQLProcessor
from rdflib_sparql.results.rdfresults import RDFResultParser

from nose.tools import eq_ as eq

DEBUG=True
DEBUG=False
DETAILEDASSERT=True

MF=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#')
QT=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-query#')

NAME=None

fails=collections.Counter()

def do_test_single(t):
    name,data,query,resfile=t

    if NAME and name!=NAME: return

    if DEBUG: print t

    try: 
        g=Graph()
        if data:
            g.load(data, format='turtle')

        if resfile.endswith('ttl'):
            resg=Graph()
            resg.load(resfile, format='turtle')
            res=RDFResultParser().parse(resg)
        else:
            res=Result.parse(file(resfile[7:]),format='xml') # relies on rdfextras

        s=SPARQLProcessor(g)

        res2=s.query(file(query[7:]).read())

        if not DETAILEDASSERT:
            eq(res.type, res2.type, 'Types do not match')
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match')
                eq(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings), 'Bindings do not match')
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, 'Ask answer does not match')
        else:

            eq(res.type, res2.type, 'Types do not match: %r != %r'%(res.type, res2.type))
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match: %r != %r'%(set(res.vars),set(res2.vars)))
                eq(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings), 'Bindings do not match: %r != %r'%(res.bindings, res2.bindings))
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, "Ask answer does not match: %r != %r"%(res.askAnswer, res2.askAnswer))


    except Exception,e:

        fails[e.message]+=1

        if DEBUG:
            print "----------------- DATA --------------------"
            print file(data[7:]).read()
            print "----------------- Query -------------------"            
            print file(query[7:]).read()
            print "----------------- Parsed ------------------"
            print parseQuery(file(query[7:]).read())
            import pdb
            pdb.set_trace()
        #nose.tools.set_trace()
        raise

    

def read_manifest(f): 

    g=Graph()
    g.load(f, format='turtle')

    for m in g.subjects(RDF.type, MF.Manifest):
        
        for col in g.objects(m, MF.include):
            for i in g.items(col):
                for x in read_manifest(i):
                    yield x 

        for col in g.objects(m,MF.entries):
            for e in g.items(col):
                
                a=g.value(e, MF.action)
                query=g.value(a, QT.query)
                data=g.value(a, QT.data)
                res=g.value(e, MF.result)
                name=g.value(e, MF.name)
                
                yield str(name),str(data),str(query),str(res)
                
                        

def test_dawg():

    for t in read_manifest("test/DAWG/data-r2/manifest-evaluation.ttl"):
        yield do_test_single, t

if __name__=='__main__':

    import sys
    if len(sys.argv)>1: NAME=sys.argv[1]
    for f, t in test_dawg():
        try: 
            f(t)
        except KeyboardInterrupt: 
            raise
        except:
            import traceback
            traceback.print_exc()

    print "\n----------------------------------------------------\n"
    for e in fails.most_common(20):
        print e
