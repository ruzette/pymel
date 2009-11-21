import pymel.util as _util
import pymel.internal.pmcmds as cmds
import pymel.internal.factories as _factories
import pymel.internal as _internal
_logger = _internal.getLogger(__name__)

def _resolveUIFunc(name):
    if isinstance(name, basestring):
        import window
        try:
            return getattr(window,name)
        except AttributeError:
            try:
                cls = getattr(dynModule,name)
                return cls.__melcmd__()
            except (KeyError, AttributeError):
                pass
    else:
        import inspect
        if inspect.isfunction(name):
            return name 
        elif inspect.isclass(name) and issubclass(name, UI):
            name.__melcmd__()
                    
    raise ValueError, "%r is not a known ui type" % name

class UI(unicode):
    def __new__(cls, name=None, create=False, **kwargs):
        """
        Provides the ability to create the UI Element when creating a class
        
            >>> n = pm.Window("myWindow",create=True)
            >>> n.__repr__()
            # Result: Window('myWindow')
        """
        if not cls is UI:
            if cls._isBeingCreated(name, create, kwargs):
                name = cls.__melcmd__(name, **kwargs)
                _logger.debug("UI: created... %s" % name)
            else:
                if '|' not in name and not issubclass(cls,Window):
                    res = [ x for x in cmds.lsUI( long=1, type=cls.__melcmd__.__name__) if x.endswith( '|' + name) ]
                    print name, res
                    if len(res) > 1:
                        raise ValueError, "found more than one UI element matching the name %s" % name
                    elif len(res) == 0:
                        raise ValueError, "could not find a UI element matching the name %s" % name
                    name = res[0]
        
        return unicode.__new__(cls,name)

    @staticmethod
    def _isBeingCreated( name, create, kwargs):
        """
        create a new node when any of these conditions occur:
           name is None
           create is True
           parent flag is set
        """
        return not name or create or ( 'q' not in kwargs and kwargs.get('parent', kwargs.get('p', None)) )
            
#    def exists():
#        try: return cls.__melcmd__(name, ex=1)
#        except: pass
        
    def __repr__(self):
        return u"%s('%s')" % (self.__class__.__name__, self)
    def parent(self):
        return PyUI( '|'.join( unicode(self).split('|')[:-1] ) )
    getParent = parent
    
    def type(self):
        try:
            return cmds.objectTypeUI(self)
        except:
            return None
    
    def shortName(self):
        return unicode(self).split('|')[-1]
    def name(self):
        return unicode(self)
    def window(self):
        return Window( self.name().split('|')[0] )
    
    delete = _factories.functionFactory( 'deleteUI', rename='delete' )
    rename = _factories.functionFactory( 'renameUI', rename='rename' )
    type = _factories.functionFactory( 'objectTypeUI', rename='type' )

    @staticmethod
    def exists(name):
        return cmds.__melcmd__( name, exists=True )
    
class Layout(UI):
    def __enter__(self):
        self.makeDefault()
        return self
    
    def __exit__(self, type, value, traceback):
        self.pop()
    
    def children(self):
        #return [ PyUI( self.name() + '|' + x) for x in self.__melcmd__(self, q=1, childArray=1) ]
        return [ PyUI( self.name() + '|' + x) for x in cmds.layout(self, q=1, childArray=1) ]
    
    getChildren = children
    
    def walkChildren(self):
        for child in self.children():
            yield child
            if hasattr(child, 'walkChildren'):
                for subChild in child.walkChildren():
                    yield subChild
        
    def addChild(self, uiType, name=None, **kwargs):
        if isinstance(uiType, basestring):
            uiType = getattr(dynModule, uiType)
        assert hasattr(uiType, '__call__'), 'argument uiType must be the name of a known ui type, a UI subclass, or a callable object'
        args = []
        if name:
            args.append(name)
        if kwargs:
            if 'parent' in kwargs or 'p' in kwargs:
                _logger.warn('parent flag is set by addChild automatically. passed value will be ignored' )
                kwargs.pop('parent', None)
                kwargs.pop('p', None) 
        kwargs['parent'] = self
        res = uiType(*args, **kwargs)
        if not isinstance(res, UI):
            res = PyUI(res)
        return res
    
    def makeDefault(self):
        """
        set this layout as the default parent
        """
        cmds.setParent(self)

    def pop(self):
        """
        set the default parent to the parent of this layout
        """
        p = self.parent()
        cmds.setParent(p)
        return p
    
# customized ui classes
class Window(Layout):
    """pymel window class"""
    __metaclass__ = _factories.MetaMayaUIWrapper

    def __exit__(self, type, value, traceback):
        self.show()
        
    def show(self):
        cmds.showWindow(self)
    
    def delete(self):
        cmds.deleteUI(self, window=True)

    def layout(self):
        # will always be one it
        if self.name() in cmds.lsUI(long=True, controlLayouts=True):
            res = self.addChild(cmds.columnLayout)
            layout = res.parent()
            res.delete()
            return layout
    
    def children(self):
        res = self.layout()
        return [res] if res else []
    
    getChildren = children
    
    def window(self):
        return self
    
    def parent(self):
        return None
    getParent = parent

class FormLayout(Layout):
    __metaclass__ = _factories.MetaMayaUIWrapper
    def attachForm(self, *args):
        kwargs = {'edit':True}
        kwargs['attachForm'] = [args]
        cmds.formLayout(self,**kwargs)
        
    def attachControl(self, *args):
        kwargs = {'edit':True}
        kwargs['attachControl'] = [args]
        cmds.formLayout(self,**kwargs)        
        
    def attachNone(self, *args):
        kwargs = {'edit':True}
        kwargs['attachNone'] = [args]
        cmds.formLayout(self,**kwargs)    
        
    def attachPosition(self, *args):
        kwargs = {'edit':True}
        kwargs['attachPosition'] = [args]
        cmds.formLayout(self,**kwargs)
        
class AutoLayout(FormLayout):
    #enumOrientation = _util.enum.Enum( 'Orientation', ['HORIZONTAL', 'VERTICAL'] )
    HORIZONTAL = 0
    VERTICAL = 1
    Orientation = _util.enum.Enum( 'Orientation', ['horizontal', 'vertical'] )

    def __new__(cls, name=None, **kwargs):
        if kwargs:
            [kwargs.pop(k) for k in ['orientation', 'ratios', 'reversed', 'spacing']]

        self = Layout.__new__(cls, name, **kwargs)
        return self
        

    def __init__(self, name=None, orientation='vertical', spacing=2, reversed=False, ratios=None, **kwargs):
        """ 
        spacing - absolute space between controls
        orientation - the orientation of the layout [ AutoLayout.HORIZONTAL | AutoLayout.VERTICAL ]
        """
        Layout.__init__(self, **kwargs)
        self._spacing = spacing
        self._orientation = self.Orientation.getIndex(orientation)
        self._reversed = reversed
        self._ratios = ratios and list(ratios) or []
    
    def __exit__(self, type, value, traceback):
        self.redistribute()
        self.pop()
        
    def flip(self):
        """Flip the orientation of the layout """
        self._orientation = 1-self._orientation
        self.redistribute(*self._ratios)
    
    def reverse(self):
        """Reverse the children order """
        self._reversed = not self._reversed
        self._ratios.reverse()
        self.redistribute(*self._ratios)
        
    def reset(self):
        self._ratios = []
        self._reversed = False
        self.redistribute()
        
    
    def redistribute(self,*ratios):
        """
        Redistribute the child controls based on the ratios.
        If not ratios are given (or not enough), 1 will be used 
        """
        
        sides = [["top","bottom"],["left","right"]]
        
        children = self.getChildArray()
        if not children:
            return
        if self._reversed: 
            children.reverse()
        
        ratios = list(ratios) or self._ratios or []
        ratios += [1]*(len(children)-len(ratios))
        self._ratios = ratios
        total = sum(ratios)       
         
        for i, child in enumerate(children):
            for side in sides[self._orientation]:
                self.attachForm(child,side,self._spacing)

            if i==0:
                self.attachForm(child,
                    sides[1-self._orientation][0],
                    self._spacing)
            else:
                self.attachControl(child,
                    sides[1-self._orientation][0],
                    self._spacing,
                    children[i-1])
            
            if ratios[i]:
                self.attachPosition(children[i],
                    sides[1-self._orientation][1],
                    self._spacing,
                    float(sum(ratios[:i+1]))/float(total)*100)
            else:
                self.attachNone(children[i],
                    sides[1-self._orientation][1])
    
    def vDistribute(self,*ratios):
        self._orientation = int(self.Orientation.vertical)
        self.redistribute(*ratios)
        
    def hDistribute(self,*ratios):
        self._orientation = int(self.Orientation.horizontal)
        self.redistribute(*ratios)

    
class TextScrollList(UI):
    __metaclass__ = _factories.MetaMayaUIWrapper
    def extend( self, appendList ):
        """ append a list of strings"""
        
        for x in appendList:
            self.append(x)
            
    def selectIndexedItems( self, selectList ):
        """select a list of indices"""
        for x in selectList:
            self.selectIndexedItem(x)

    def removeIndexedItems( self, removeList ):
        """remove a list of indices"""
        for x in removeList:
            self.removeIndexedItem(x)
                
    def selectAll(self):
        """select all items"""
        numberOfItems = self.getNumberOfItems()
        self.selectIndexedItems(range(1,numberOfItems+1))

class OptionMenu(UI):
    __metaclass__ = _factories.MetaMayaUIWrapper
    def addMenuItems( self, items, title=None):
        """ Add the specified item list to the OptionMenu, with an optional 'title' item """ 
        if title:
            cmds.menuItem(l=title, en=0, parent=self)
        for item in items:
            cmds.menuItem(l=item, parent=self)
            
    def clear(self):  
        """ Clear all menu items from this OptionMenu """
        for t in self.getItemListLong() or []:
            cmds.deleteUI(t)
    addItems = addMenuItems

class UITemplate(object):
    """
    from pymel.core import *
    
    template = ui.UITemplate( 'ExampleTemplate', force=True )
    
    template.define( button, width=100, height=40, align='left' )
    template.define( frameLayout, borderVisible=True, labelVisible=False )
    
    #    Create a window and apply the template.
    #
    with window():
        with template:
            with columnLayout( rowSpacing=5 ):
                with frameLayout():
                    with columnLayout():
                        button( label='One' )
                        button( label='Two' )
                        button( label='Three' )
                
                with frameLayout():
                    with columnLayout():
                        button( label='Red' )
                        button( label='Green' )
                        button( label='Blue' )
    """
    def __init__(self, name=None, force=False):
        if name and force and cmds.uiTemplate( name, exists=True ):
            cmds.deleteUI( name, uiTemplate=True )
        args = [name] if name else []
        
        self._name = cmds.uiTemplate( *args )
    
    def __repr__(self):
        return '%s(%r)' % ( self.__class__.__name__, self._name)  
     
    def __enter__(self):
        self.push()
        return self
    
    def __exit__(self, type, value, traceback):
        self.pop()

    def name(self):
        return self._name
    
    def push(self):
        cmds.setUITemplate(self._name, pushTemplate=True)
        
    def pop(self):
        cmds.setUITemplate( popTemplate=True)

    def define(self, uiType, **kwargs):
        """
        uiType can be:
            - a ui function or class
            - the name of a ui function or class
            - a list or tuple of the above
        """
        if isinstance(uiType, (list,tuple)):
            funcs = [ _resolveUIFunc(x) for x in uiType ] 
        else:
            funcs = [_resolveUIFunc(uiType)]
        kwargs['defineTemplate'] = self._name
        for func in funcs:
            func(**kwargs)
    
    @staticmethod
    def exists(name):
        return cmds.uiTemplate( name, exists=True )


dynModule = _util.LazyLoadModule(__name__, globals())

def _createUIClasses():

    for funcName in _factories.uiClassList:
        # Create Class
        classname = _util.capitalize(funcName)
        try:
            cls = dynModule[classname]
        except KeyError:
            if classname.endswith('Layout'):
                bases = (Layout,)
            else:
                bases = (UI,)
            dynModule[classname] = (_factories.MetaMayaUIWrapper, (classname, bases, {}) )

_createUIClasses()
      
class VectorFieldGrp( dynModule.FloatFieldGrp ):
    def __new__(cls, name=None, create=False, *args, **kwargs):
        if create:
            kwargs.pop('nf', None)
            kwargs['numberOfFields'] = 3
            name = cmds.floatFieldGrp( name, *args, **kwargs)

        return dynModule.FloatFieldGrp.__new__( cls, name, create=False, *args, **kwargs )
        
    def getVector(self):
        import datatypes
        x = cmds.floatFieldGrp( self, q=1, v1=True )
        y = cmds.floatFieldGrp( self, q=1, v2=True )
        z = cmds.floatFieldGrp( self, q=1, v3=True )
        return datatypes.Vector( [x,y,z] )
    
    def setVector(self, vec):
        cmds.floatFieldGrp( self, e=1, v1=vec[0], v2=vec[1], v3=vec[2] )

class PathButtonGrp( dynModule.TextFieldButtonGrp ):
    def __new__(cls, name=None, create=False, *args, **kwargs):
        
        if create:
            kwargs.pop('bl', None)
            kwargs['buttonLabel'] = 'Browse'
            kwargs.pop('bl', None)
            kwargs['buttonLabel'] = 'Browse'
            kwargs.pop('bc', None)
            kwargs.pop('buttonCommand', None)

            name = cmds.textFieldButtonGrp( name, *args, **kwargs)
            
            def setPathCB(name):
                f = promptForPath()
                if f:
                    cmds.textFieldButtonGrp( name, e=1, text=f)
            
            import windows
            cb = windows.Callback( setPathCB, name ) 
            cmds.textFieldButtonGrp( name, e=1, buttonCommand=cb )
            
        return dynModule.TextFieldButtonGrp.__new__( cls, name, create=False, *args, **kwargs )
        
    def setPath(self, path):
        self.setText( path )
       
    def getPath(self):
        import system
        return system.Path( self.getText() )

_uiTypesToCommands = {
    'rowGroupLayout' : 'rowLayout',
    'TcolorIndexSlider' : 'rowLayout',
    'TcolorSlider' : 'rowLayout'
    }

def PyUI(strObj, uiType=None):

    if not uiType:
        try:
            uiType = cmds.objectTypeUI(strObj)
            uiType = _uiTypesToCommands.get(uiType, uiType)
        except RuntimeError:
            # we cannot query the type of rowGroupLayout children: check common types for these
            for control in 'checkBox floatField button floatSlider intSlider ' \
                    'floatField textField intField optionMenu radioButton'.split():
                if getattr(cmds, control)( strObj, ex=1, q=1):
                    uiType = control
                    break
            if not uiType:
                uiType = 'UI'

    try:
        return getattr(dynModule, _util.capitalize(uiType) )(strObj)
    except AttributeError:
        return UI(strObj)

dynModule._lazyModule_update()
