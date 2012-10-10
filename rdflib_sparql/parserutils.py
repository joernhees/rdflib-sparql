
from types import MethodType
from collections import OrderedDict

from pyparsing import TokenConverter, ParseResults

from rdflib import BNode, Variable, Literal, URIRef

DEBUG=True
DEBUG=False
if DEBUG: 
    import traceback

"""
Utility classes for creating an abstract-syntax tree out with pyparsing actions

Lets you label and group parts of parser production rules

For example:

# [5] BaseDecl ::= 'BASE' IRIREF
BaseDecl = Comp('Base', Keyword('BASE') + Param('iri',IRIREF))

After parsing, this gives you back an CompValue object, 
which is a dict/object with the paramters specified. 
So you can access the parameters are attributes or as keys: 

baseDecl.iri 

Comp lets you set an evalFn that is bound to the eval method of
the resulting CompValue 


"""


# This is an alternative 

# Comp('Sum')( Param('x')(Number) + '+' + Param('y')(Number) )

def value(ctx, val, variables=False):

    """
    utility function for evaluating something...
    """

    if isinstance(val, Expr): 
        return val.eval(ctx) # recurse?
    elif isinstance(val, CompValue):
        if val.name=='literal': 
            return ctx.absolutize(val)
        elif val.name=='pname':
            return ctx.absolutize(val)
        else: 
            raise Exception("What do I do with this CompValue? %s"%val)

    elif isinstance(val, list): 
        return [value(ctx,x) for x in val]

    elif isinstance(val, (BNode, Variable)):
        r=ctx[val] 
        if r!=None: return r

        # not bound
        if variables:
            return val
        else: 
            raise NotBoundError

    elif isinstance(val, ParseResults) and len(val)==1:
        return value(ctx,val[0])

    elif isinstance(val, URIRef): 
        return ctx.absolutize(val) 

    else: 
        return val



class ParamValue(object): 
    """ 
    The result of parsing a Param 
    This just keeps the name/value
    All cleverness is in the CompValue
    """
    def __init__(self, name, tokenList, isList): 
        self.isList=isList
        self.name=name
        if isinstance(tokenList, (list,ParseResults)) and len(tokenList)==1: 
            tokenList=tokenList[0]

        self.tokenList=tokenList

class Param(TokenConverter): 
    """
    A pyparsing token for labelling a part of the parse-tree
    if isList is true repeat occurrences of ParamList have 
    their values merged in a list
    """
    def __init__(self, name, expr, isList=False):
        self.name=name
        self.isList=isList
        TokenConverter.__init__(self, expr)
        self.addParseAction(self.postParse2)

    def postParse2(self, tokenList): 
        return ParamValue(self.name, tokenList, self.isList)

class ParamList(Param): 
    """
    A shortcut for a Param with isList=True
    """
    def __init__(self,name,expr):
        Param.__init__(self,name,expr,True)

class plist(list):
    """this is just a list, but we want our own type to check for"""

    pass

class CompValue(OrderedDict):

    """
    The result of parsing a Comp
    Any included Params are avaiable as Dict keys 
    or as attributes

    """

    def __init__(self, name, **values):        
        OrderedDict.__init__(self)
        self.name=name
        self.update(values)
            
    def __str__(self):
        return self.name+"_"+OrderedDict.__str__(self)

    def __repr__(self):
        return self.name+"_"+OrderedDict.__repr__(self)

    def _value(self,val,variables=False): 
        if self.ctx!=None: 
            return value(self.ctx, val, variables)
        else: 
            return val
            
    def __getitem__(self,a): 
        return self._value(OrderedDict.__getitem__(self,a))

    def get(self,a,variables=False):
        return self._value(OrderedDict.__getitem__(self,a),variables)

    def __getattr__(self,a):
        # Hack hack: OrderedDict relies on this
        if a=='_OrderedDict__root': raise AttributeError
        try: 
            return self[a]
        except KeyError: 
            #raise AttributeError('no such attribute '+a)
            return None

class Expr(CompValue): 
    """
    A CompValue that is evaluatable    
    """

    def __init__(self, name, evalfn=None, **values):        
        super(Expr,self).__init__(name,**values)

        self._evalfn=None
        if evalfn:
            self._evalfn=MethodType(evalfn, self, CompValue)

    def eval(self, ctx={}): 
        try: 
            self.ctx=ctx
            return self._evalfn(ctx)
        except NotBoundError:
            raise
        except Exception,e: 
            if DEBUG:
                traceback.print_exc()
            raise SPARQLError(e)
        finally: 
            self.ctx=None



class Comp(TokenConverter): 

    """
    A pyparsing token for grouping together things with a label 
    Any sub-tokens that are not Params will be ignored. 

    Returns CompValue / Expr objects - depending on whether evalFn is set. 
    """

    def __init__(self, name, expr): 
        TokenConverter.__init__(self, expr)
        self.name=name
        self.evalfn=None

    def postParse(self, instring, loc, tokenList):

        if self.evalfn:
            res=Expr(self.name)
            res._evalfn=MethodType(self.evalfn, res, CompValue)
        else:
            res=CompValue(self.name)

        for t in tokenList: 
            if isinstance(t,ParamValue):
                if t.isList:
                    if not t.name in res: res[t.name]=plist()
                    res[t.name].append(t.tokenList)
                else:
                    res[t.name]=t.tokenList
                #res.append(t.tokenList)
            #if isinstance(t,CompValue):
            #    res.update(t)
        return res

    def setEvalFn(self,evalfn):
        self.evalfn=evalfn
        return self
    

if __name__=='__main__':
    from pyparsing import Word, nums
    import sys

    Number = Word(nums)
    Number.setParseAction(lambda x: int(x[0]))
    Plus = Comp('plus', Param('a',Number) + '+' + Param('b',Number) )
    Plus.setEvalFn(lambda self,ctx: self.a+self.b)

    r=Plus.parseString(sys.argv[1])
    print r
    print r[0].eval({})

# hurrah for circular imports
from rdflib_sparql.sparql import SPARQLError, NotBoundError