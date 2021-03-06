"""
Creates safe cross referencing

Safe cross-referencing skips failed xref's
"""
from __future__ import print_function
from typing import List, Dict, Any
from six import iteritems, itervalues
import traceback

from numpy import zeros, argsort, arange, array_equal
from pyNastran.bdf.bdf_interface.cross_reference import XrefMesh

class SafeXrefMesh(XrefMesh):
    """
    Links up the various cards in the BDF.
    """
    def __init__(self):
        """
        The main BDF class defines all the parameters that are used.
        """
        XrefMesh.__init__(self)

    # def geom_check(self):
        # """
        # Performs various geometry checks
          # 1.  nodal uniqueness on elements
        # """
        # for elem in model.elements:
            # elem.check_unique_nodes()

    def safe_cross_reference(self, xref=True,
                             xref_nodes=True,
                             xref_elements=True,
                             xref_nodes_with_elements=True,
                             xref_properties=True,
                             xref_masses=True,
                             xref_materials=True,
                             xref_loads=True,
                             xref_constraints=True,
                             xref_aero=True,
                             xref_sets=True,
                             xref_optimization=True,
                             debug=True):
        """
        Performs cross referencing in a way that skips data gracefully.

        .. warning:: not fully implemented
        """
        if not xref:
            return
        self.log.debug("Safe Cross Referencing...")
        if xref_nodes:
            self._cross_reference_nodes()
            self._cross_reference_coordinates()

        if xref_elements:
            self._safe_cross_reference_elements()
        if xref_properties:
            self._cross_reference_properties()
        if xref_masses:
            self._cross_reference_masses()
        if xref_materials:
            self._cross_reference_materials()

        if xref_sets:
            self._cross_reference_sets()
        if xref_aero:
            self._safe_cross_reference_aero()
        if xref_constraints:
            self._safe_cross_reference_constraints()
        if xref_loads:
            self._safe_cross_reference_loads(debug=debug)
        if xref_sets:
            self._cross_reference_sets()
        if xref_optimization:
            self._cross_reference_optimization()
        if xref_nodes_with_elements:
            self._cross_reference_nodes_with_elements()
        self.pop_xref_errors()

    def _safe_cross_reference_constraints(self):
        # type: () -> None
        """
        Links the SPCADD, SPC, SPCAX, SPCD, MPCADD, MPC, SUPORT,
        SUPORT1, SESUPORT cards.
        """
        for spcadds in itervalues(self.spcadds):
            for spcadd in spcadds:
                spcadd.safe_cross_reference(self)
        for spcs in itervalues(self.spcs):
            for spc in spcs:
                spc.safe_cross_reference(self)
        for spcoffs in itervalues(self.spcoffs):
            for spcoff in spcoffs:
                spcoff.safe_cross_reference(self)

        for mpcadds in itervalues(self.mpcadds):
            for mpcadd in mpcadds:
                mpcadd.safe_cross_reference(self)
        for mpcs in itervalues(self.mpcs):
            for mpc in mpcs:
                mpc.safe_cross_reference(self)

        for suport in self.suport:
            suport.safe_cross_reference(self)

        for suport1_id, suport1 in iteritems(self.suport1):
            suport1.safe_cross_reference(self)

        for se_suport in self.se_suport:
            se_suport.safe_cross_reference(self)

    def _safe_cross_reference_aero(self):
        # type: () -> None
        """
        Links up all the aero cards
          - CAEROx, PAEROx, SPLINEx, AECOMP, AELIST, AEPARAM, AESTAT, AESURF, AESURFS
        """
        for caero in itervalues(self.caeros):
            caero.safe_cross_reference(self)

        for paero in itervalues(self.paeros):
            paero.safe_cross_reference(self)

        for trim in itervalues(self.trims):
            trim.safe_cross_reference(self)

        for csschd in itervalues(self.csschds):
            csschd.safe_cross_reference(self)

        for spline in itervalues(self.splines):
            spline.safe_cross_reference(self)

        for aecomp in itervalues(self.aecomps):
            aecomp.safe_cross_reference(self)

        for aelist in itervalues(self.aelists):
            aelist.safe_cross_reference(self)

        for aeparam in itervalues(self.aeparams):
            aeparam.safe_cross_reference(self)

        #for aestat in itervalues(self.aestats):
            #aestat.safe_cross_reference(self)

        for aesurf in itervalues(self.aesurf):
            aesurf.safe_cross_reference(self)

        for aesurfs in itervalues(self.aesurfs):
            aesurfs.safe_cross_reference(self)

        for flutter in itervalues(self.flutters):
            flutter.safe_cross_reference(self)

        if self.aero:
            self.aero.safe_cross_reference(self)
        if self.aeros:
            self.aeros.safe_cross_reference(self)

        if 0:  # only support CAERO1
            ncaeros = len(self.caeros)
            if ncaeros > 1:
                # we don't need to check the ncaeros=1 case
                i = 0
                min_maxs = zeros((ncaeros, 2), dtype='int32')
                for eid, caero in sorted(iteritems(self.caeros)):
                    min_maxs[i, :] = caero.min_max_eid
                    i += 1
                isort = argsort(min_maxs.ravel())
                expected = arange(ncaeros * 2, dtype='int32')
                if not array_equal(isort, expected):
                    msg = 'CAERO element ids are inconsistent\n'
                    msg += 'isort = %s' % str(isort)
                    raise RuntimeError(msg)

            #'AERO',     ## aero
            #'AEROS',    ## aeros
            #'GUST',     ## gusts
            #'FLUTTER',  ## flutters
            #'FLFACT',   ## flfacts
            #'MKAERO1', 'MKAERO2',  ## mkaeros
            #'AECOMP',   ## aecomps
            #'AEFACT',   ## aefacts
            #'AELINK',   ## aelinks
            #'AELIST',   ## aelists
            #'AEPARAM',  ## aeparams
            #'AESTAT',   ## aestats
            #'AESURF',  ## aesurfs

    def _safe_cross_reference_elements(self):
        # type: () -> None
        """
        Links the elements to nodes, properties (and materials depending on
        the card).
        """
        missing_safe_xref = set([])
        for elem in itervalues(self.elements):
            if hasattr(elem, 'safe_cross_reference'):
                elem.safe_cross_reference(self)
            else:
                elem.cross_reference(self)
                missing_safe_xref.add(elem.type)

        for elem in itervalues(self.rigid_elements):
            if hasattr(elem, 'safe_cross_reference'):
                elem.safe_cross_reference(self)
            else:
                missing_safe_xref.add(elem.type)
                elem.cross_reference(self)
        #if missing_safe_xref:
            #self.log.warning('These cards dont support safe_xref; %s' % str(list(missing_safe_xref)))

    def _safe_cross_reference_loads(self, debug=True):
        # type: (bool) -> None
        """
        Links the loads to nodes, coordinate systems, and other loads.
        """
        for (lid, load_combinations) in iteritems(self.load_combinations):
            for load_combination in load_combinations:
                load_combination.safe_cross_reference(self)

        for (lid, loads) in iteritems(self.loads):
            for load in loads:
                load.safe_cross_reference(self)

        for (lid, sid) in iteritems(self.dloads):
            for load in sid:
                load.safe_cross_reference(self)
        for (lid, sid) in iteritems(self.dload_entries):
            for load in sid:
                load.safe_cross_reference(self)

        for key, darea in iteritems(self.dareas):
            darea.safe_cross_reference(self)
        for key, dphase in iteritems(self.dphases):
            dphase.safe_cross_reference(self)

    def safe_empty_nodes(self, nids, msg=''):
        """safe xref version of self.Nodes(nid, msg='')"""
        nodes = []
        missing_nodes = []
        for nid in nids:
            try:
                node = self.EmptyNode(nid)
            except KeyError:
                node = nid
                missing_nodes.append(nid)
            nodes.append(node)
        if missing_nodes:
            missing_nodes.sort()
            self.log.warning('Nodes %s are missing%s' % (str(missing_nodes), msg))
        return nodes, missing_nodes

    def safe_get_nodes(self, nids, msg=''):
        """safe xref version of self.Nodes(nid, msg='')"""
        nodes = []
        msgi = ''
        for nid in nids:
            try:
                node = self.Node(nid)
            except KeyError:
                node = nid
                msgi += msg % (nid)
            nodes.append(nid)
        return nodes, msgi

    def safe_get_elements(self, eids, msg=''):
        """safe xref version of self.Elements(eid, msg='')"""
        elements = []
        msgi = ''
        for eid in eids:
            try:
                element = self.Element(eid)
            except KeyError:
                element = eid
                msgi += msg % (eid)
            elements.append(element)
        return elements, msgi
