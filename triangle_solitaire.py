#!/usr/bin/python

import pygame
from pygame.locals import *
import random
import fractions
rat = fractions.Fraction
import math

"""
Mostly internal details are discussed in these comments. See readme.txt for instructions for the user.

I use the L-orientation in implementation, but when drawing we will move the top point
instructions.txt so we have an equilateral grid.

Objects:
* dots: a set of elements of \Z^2
* triangles: triangles (equilateral in \Delta-orientation) where we have built a 
line. The triangle knows the orientation of the line, it's determined by a single
rational point on the boundary. It also knows which dots are associated with the
line, and they are _black_. A triangle can be endangered_, that's a bool. Also _invasive_.
* dots not part of line of any triangle are _gray_

Whenever a new triangle is formed (because two triangles join), we may get that
some triangle intersects the new one. If such a triangle is entirely inside a newly
formed triangle, it just turns gray immediately.

Other such triangles are all marked as endangered and the new triangle is marked
invasive. We cannot merge any triangles that are endangered or invasive, or 
such that after the merge they would touch an endangered or invasive one.

We can get rid of an endangered triangle T as follows, where U is invasive.
If T has a corner inside U, then rotate its line so that that line starts
from that corner, then turn everything in U gray and you are left with a smaller
triangle in place of T. If U has a corner inside T, then put all dots of T
on the side that goes through U, cutting T into two triangles.

Finally, an invasive triangle becomes non-invasive once we remove the endangereds.

In the implementation, we will use a PyGame loop and at all times we draw the situation.
We have a current operation that's happening, which can be to merge or undanger an
endangered. In each case, we want to rotate the line of some triangle to some
other point. We will calculate the next orientation that changes something, and
then we lerp toward that one...

ORDERS: for vertices, btm-left = 0, top = 1, right = 2
for lines, left, bottom, ne [sic]
"""



# these are for the state machine that tells us what we're doing
IDLE = 1
MERGING = 2
KILL = 3
NORMALIZE = 4
tri1 = None 
tri2 = None
tri3 = None
EDITING = 5
SOLITAIRE = 6

idles = [IDLE, EDITING, SOLITAIRE]

ORIENT = 7
FALL = 8

murderer = None

scale = 30
xpos, ypos = 0, 0 # logical position at center of screen
width, height = 1000, 700

chosentriangle = None
MARGIN = 0.3

speed = rat(1,20)






def from_s(s):
    dots = set()
    s = s.strip()
    lines = s.split("\n")
    y = len(lines)-1
    for l in lines:
        x = 0
        for c in l:
            if c == "1":
                dots.add((x, y))
            x += 1
        y -= 1
    return dots
        
    

def vadd(a, b):
    return a[0]+b[0], a[1]+b[1]

def vsub(a, b):
    return a[0]-b[0], a[1]-b[1]

def dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def smul(s, v):
    return s*v[0], s*v[1]

def rotate_right(v):
    return (v[1], -v[0])

def rotate_left(v):
    return (-v[1], v[0])

def sqrdist(u, v):
    return (v[0]-u[0])**2 + (v[1]-u[1])**2

def right_of_line(line, pos):
    a = line[0]
    b = line[1]
    bma = vsub(b, a)
    rel = vsub(pos, a)
    return dot(rotate_right(bma), rel) >= 0

def triangle_contains(triangle_as_lines, pos):
    for line in triangle_as_lines:
        if not right_of_line(line, pos):
            #print("not tirhg", line, pos)
            return False
    return True

def line_intersection(line1, line2):
    #print(line1, line2, "impi")
    a, b = line1
    b = vsub(b, a)
    if b == (0, 0):
        raise Exception("o no")
    c, d = line2
    d = vsub(d, c)
    """
    line1 = a + tb
    line2 = c + ud
    
    ax + t bx = cx + u dx
    ay + t by = cy + u dy

    ax (by/bx) + t by = (by/bx)(cx + u dx)
    ay + t by = cy + u dy

    ax (by/bx) - ay = (by/bx) cx + (by/bx) u dx - cy - u dy

    ax (by/bx) - ay = (by/bx) cx - cy + u ((by/bx) dx - dy)

    (ax (by/bx) - ay + cy - (by/bx) cx) / ((by/bx) dx - dy) = u

    t = (cy + u dy - ay) / by
    """
    if b[0] != 0:
        #b0 = b0
        u = (a[0] * (b[1]/b[0]) - a[1] + c[1] - (b[1]/b[0]) * c[0]) / ((b[1]/b[0]) * d[0] - d[1])
        # t = (c[1] + u * d[1] - a[1]) / b[1]
        # assert vadd(c, smul(u, d)) == vadd(a, smul(t, b))
        return vadd(c, smul(u, d))
    else:
        line1 = rotate_right(line1[0]), rotate_right(line1[1])
        line2 = rotate_right(line2[0]), rotate_right(line2[1])
        inte = line_intersection(line1, line2)
        #print("had to rot", inte)
        return rotate_left(inte)

def set_merge_orientations(tri1, tri2):
    flip, side = tri1.neighbor_side(tri2)
    if flip:
        tri1, tri2 = tri2, tri1

    # flipped so that tri2's corner is on a side of tri1

    l = (tri1.corners[2 - side], tri2.corners[2 - side])
    
    if tri1.size > 1 and tri2.size > 1:
    
        # now, a corner of tri2 is on a side of tri1,
        # and that side dictated by var side
        # 2 - side is the corner point opposite side
        tri1.set_merge_orientation_from_pt(side, line_intersection(tri1.get_lines()[side], l))
        tri2.set_merge_orientation_from_pt(side, line_intersection(tri2.get_lines()[side], l))

    elif tri1.size == 1 and tri2.size == 1:

        assert tri1.corners[0] == tri1.corners[1] == tri1.corners[2]
        assert tri2.corners[0] == tri2.corners[1] == tri2.corners[2]

        pt1 = tri1.corners[0]
        pt2 = tri2.corners[0]

        if pt2 == vadd(pt1, (1, 0)) or pt1 == vadd(pt2, (1, 0)):
            tri1.set_wanted_orientation(0)
            tri2.set_wanted_orientation(0)
        if pt2 == vadd(pt1, (1, -1)) or pt1 == vadd(pt2, (1, -1)):
            tri1.set_wanted_orientation(1)
            tri2.set_wanted_orientation(1)
        if pt2 == vadd(pt1, (0, 1)) or pt1 == vadd(pt2, (0, 1)):
            tri1.set_wanted_orientation(2)
            tri2.set_wanted_orientation(2)

    elif tri1.size > 1:
        #print("heresy", side)
        li = line_intersection(tri1.get_lines()[side], l)
        #print("inter", li)
        assert tri2.size == 1
        tri1.set_merge_orientation_from_pt(side, li)
        #print(tri1.wanted_orientation, tri1.corners[0])
        tri2.set_wanted_orientation(tri1.wanted_orientation)
        #print(tri2.wanted_orientation, tri2.corners[0])

        #print(tri1.next_line)

    elif tri2.size > 1:
        assert tri1.size == 1
        tri2.set_merge_orientation_from_pt(side, line_intersection(tri2.get_lines()[side], l))
        tri1.set_wanted_orientation(tri2.wanted_orientation)

    """
    if side == 0:
        l = (tri1.corners[2], tri2.corners[2])
        tri1.set_merge_orientation_from_pt(0, line_intersection(tri1.get_lines(0), l))
        tri2.set_merge_orientation_from_pt(0, line_intersection(tri2.get_lines(0), l))
    elif side == 1:
        l = (tri1.corners[1], tri2.corners[1])
        tri1.set_merge_orientation_from_pt(1, line_intersection(tri1.get_lines(1), l))
        tri2.set_merge_orientation_from_pt(1, line_intersection(tri2.get_lines(1), l))
    """
        

class Triangle:
    def __init__(self, v, dots):
        self.dots = dots # this is so _in theory_ the triangle could be smart about points when there is excess
        self.size = 1
        self.current_line = set([v])
        self.corners = [v, v, v]
        # the line is determined by a number [0, 3), 0 1 2 mean left down ne,
        # and remainder means dist of endpoint on that side, clockwise
        self.set_orientation(rat(0, 1))
        # self.wantedpoint = None
        self.timer = 0

    def get_lines(self, margin = 0):
        half = rat(1, 2)
        #print ("getting lines", margin)
        left_line = vadd(self.corners[0], (-margin, -1)), vadd(self.corners[1], (-margin, 1))
        ne_line = vadd(self.corners[1], (margin*half-1, margin*half+1)), vadd(self.corners[2], (margin*half+1, margin*half-1))
        bottom_line = vadd(self.corners[2], (1, -margin)), vadd(self.corners[0], (-1, -margin))
        #print(left_line, ne_line, bottom_line)
        return left_line, bottom_line, ne_line

    def contains(self, pos, margin = MARGIN):
        lines = self.get_lines(margin)
        return triangle_contains(lines, pos)

    def intersects(self, other):
        for c in self.corners:
            if other.contains(c):
                return True
        for c in other.corners:
            if self.contains(c):
                return True
        return False

    def get_drawn_lines(self):
        return [self.get_line_from_orientation(self.get_pretend_orientation())]

    def get_thickened(self, margin):
        if margin == 0 and self.size == 1:
            return self.corners
        #print(margin)
        left_line, bottom_line, ne_line = self.get_lines(margin)
        points = []
        #print(left_line, #ne_line,
            #sbottom_line)
        points.append(line_intersection(left_line, bottom_line))
        #print(points)
        #ab = bbbb
        points.append(line_intersection(left_line, ne_line))
        points.append(line_intersection(ne_line, bottom_line))
        return points

    # calculate the dots that should be on here
    # let's just to a triple
    def calculate_line(self, ori):
        #print(ori)
        ori = ori % 3

        # now we start at startpoint, and
        # we do moves in order, as continuation take the one
        # that is closer to line determined by ori
        
        side = int(ori)
        if side == 0:
            startpoint = self.corners[2]
            moves = [(-1, 0), (-1, 1)]
        if side == 1:
            startpoint = self.corners[1]
            moves = [(1, -1), (0, -1)]
        if side == 2:
            startpoint = self.corners[0]
            moves = [(0, 1), (1, 0)]

        # we need to distort the grid a little
        right_move = vsub(moves[1], moves[0])
        #print("size,2", self.size, right_move)
        right_epsilon = smul(rat(1,20*self.size), right_move) # smul(rat(1,345987345*self.size), right_move)

        #lerpo = ori - side
        #a, b = side_to_endpoints_cw(side)
        #av, bv = self.corners[a], self.corners[b]

        # the line we actually want goes from startpoint to...
        endpoint = self.point_from_orientation(ori)
        #print(endpoint)
        
        # calculate length of projection on its complement (up to random order-preserving stretch)
        def projdist(v):
            # obviously we should just calc these once but it doesn't _really_ matter, and it's clearer this way maybe
            relline = vsub(endpoint, startpoint) 
            relv = vsub(v, startpoint)
            rotline = rotate_left(relline)
            return abs(dot(relv, rotline))

        linepoints = []
        currpoint = startpoint
        linepoints.append(currpoint)
        # currpoint = vadd(startpoint, (rat(1010010101,24359873489573248),rat(974984353,194875394275934857)))        

        for i in range(self.size - 1):

            neps = self.size - 2 - i
            
            dists = []
            for m in moves:
                p = vadd(vadd(currpoint, m), smul(neps, right_epsilon))
                dists.append(projdist(p))
            if dists[0] <= dists[1]:
                currpoint = vadd(currpoint, moves[0])
            else:
                currpoint = vadd(currpoint, moves[1])
                
            linepoints.append(currpoint)

        return set(linepoints)

    def point_from_orientation(self, ori):
        side = int(ori)
        a, b = side_to_endpoints_cw(side)
        av, bv = self.corners[a], self.corners[b]
        t = ori - side
        return vadd(av, smul(t, vsub(bv, av)))

    def get_line_from_orientation(self, ori):
        pt = self.point_from_orientation(ori)
        side = int(ori)
        return self.corners[2 - side], pt
        
    # given another triangle, are we buddies?
    def neighbor_side(self, other, flip = False):
        # is it on the left?
        if other.corners[2][0] == self.corners[0][0] - 1 and other.corners[2][1] >= self.corners[0][1] and other.corners[2][1] <= self.corners[1][1] + 1:
            return (flip, 0)
        # btm?
        if other.corners[1][1] == self.corners[0][1] - 1 and other.corners[1][0] >= self.corners[0][0] and other.corners[1][0] <= self.corners[2][0] + 1:
            return (flip, 1)
        # is it on the ne?
        if sum(other.corners[0]) == sum(self.corners[1]) + 1 and other.corners[0][0] >= self.corners[1][0] and other.corners[0][1] >= self.corners[2][1]:
            return (flip, 2)
        if flip == True:
            return None
        else:
            return other.neighbor_side(self, True)

    def is_neighbor(self, other):
        return self.neighbor_side(other) != None

    def die(self, other):
        #print(self.corners[0], "dije")
        #print(other.corners[0])
        c0 = self.corners[0]
        c1 = self.corners[1]
        c2 = self.corners[2]
        if other.contains(c0) and other.contains(c1) and other.contains(c2):
            self.set_wanted_orientation(self.orientation)
        elif other.contains(c0):
            self.set_wanted_orientation(2) # or 0
        elif other.contains(c1):
            self.set_wanted_orientation(1) # or 2
        elif other.contains(c2):
            self.set_wanted_orientation(0) # or 1
        elif self.contains(other.corners[0]):
            self.set_wanted_orientation(1)
        elif self.contains(other.corners[1]):
            self.set_wanted_orientation(0)
        elif self.contains(other.corners[2]):
            self.set_wanted_orientation(2)

    def merge_with_murderer(self, murderer):
        containeds = set()
        minix = None
        miniy = None
        maxix = None
        maxiy = None
        for c in self.current_line:
            if not murderer.contains(c):
                continue
            if minix == None or c[0] < minix:
                minix = c[0]
            if maxix == None or c[0] > maxix:
                maxix = c[0]
            if miniy == None or c[1] < miniy:
                miniy = c[1]
            if maxiy == None or c[1] > maxiy:
                maxiy = c[1]
        if minix == None:
            return []

        dems = []
        
        if self.orientation == 0:
            #print("this")
            # in this case, we can look at minix, maxix
            if minix > self.corners[0][0]: # there is a leftmost triangle to construct
                #print("yep", minix, self.corners[0])
                left = Triangle((0, 0), self.dots)
                left.corners = self.corners[:]
                left.size = int(minix - self.corners[0][0])
                left.calculate_corners_from_one(0)
                #print(left.corners, "issu")
                #print(left.size)
                #print("I FAILE NOW")
                left.calculate_line(0)
                dems.append(left)

            if maxix < self.corners[2][0]:
                #print("yeb", maxix, self.corners[2])
                right = Triangle((0, 0), self.dots)
                right.corners = self.corners[:]
                right.size = int(self.corners[2][0] - maxix)
                right.calculate_corners_from_one(2)
                #print(right.corners, "rittus")
                dems.append(right)

        if self.orientation == 1:
            # in this case, we can look at minix, maxix
            if minix > self.corners[1][0]: # there is a leftmost triangle to construct
                left = Triangle((0, 0), self.dots)
                left.corners = self.corners[:]
                left.size = int(minix - self.corners[1][0])
                left.calculate_corners_from_one(1)
                dems.append(left)

            if maxix < self.corners[2][0]:
                right = Triangle((0, 0), self.dots)
                right.corners = self.corners[:]
                right.size = int(self.corners[2][0] - maxix)
                right.calculate_corners_from_one(2)
                dems.append(right)

        if self.orientation == 2:
            # in this case, we can look at minix, maxix
            if miniy > self.corners[0][1]: # there is a btmmost triangle to construct
                left = Triangle((0, 0), self.dots)
                left.corners = self.corners[:]
                left.size = int(miniy - self.corners[0][1])
                left.calculate_corners_from_one(0)
                dems.append(left)

            if maxiy < self.corners[1][1]:
                right = Triangle((0, 0), self.dots)
                right.corners = self.corners[:]
                right.size = int(self.corners[1][1] - maxiy)
                right.calculate_corners_from_one(1)
                dems.append(right)

        for d in dems:
            d.set_orientation(self.orientation)
            #print(d.orientation, "orientation")

            assert d.dots == self.dots
            
            #self.current_line = set([v])
        #self.corners = [v, v, v]
        # the line is determined by a number [0, 3), 0 1 2 mean left down ne,
        # and remainder means dist of endpoint on that side, clockwise
        #self.set_orientation(rat(0, 1))
        # self.wantedpoint = None
        #self.timer = 0
        
        #print(dems, "reto")

        demsus = dems[:]
        for k in self.dots:
            if k == (0,2):
                #print("keuhu")
                pass
            if self.contains(k):
                #print("yes cont")
                for q in demsus:
                    if q.contains(k):
                        #print("qqq", q)
                        break
                else:
                    #print("herer")
                    if not murderer.contains(k):
                        #print("o o")
                        dems.append(Triangle(k, self.dots))
                        pass
        #print("ok")

        return dems

    def set_orientation(self, ori):
        assert type(ori) == fractions.Fraction or type(ori) == int
        self.orientation = ori
        self.pretend_orientation = ori
        self.calculate_current_line()

    def get_pretend_orientation(self):
        return self.pretend_orientation % 3

    # find an orientation between a and b such that line differs by exactly one from current_line
    # we should find a, b such that diff at a is 0 and diff at b is 1: and diff betw a and b is accu
    def technical_binary_thing(self, a, b, accu = 100):
        
        self.techno_counter += 1
        cl = self.current_line
        al = self.calculate_line(a)
        bl = self.calculate_line(b)
        adiff = al.symmetric_difference(cl)
        bdiff = bl.symmetric_difference(cl)

        #print("kiliman", a, len(adiff), b, len(bdiff))
        
        if len(adiff) == 0 and len(bdiff) == 2 and abs(b - a) < accu:
            return b

        if len(bdiff) == 0:
            b = a + (b - a) * 2 # rat(5,2)
            return self.technical_binary_thing(a, b, accu)

        #print("vs", a, len(adiff), b, len(bdiff))
        
        assert len(adiff) == 0
        mid = (a + b) / 2
        midl = self.calculate_line(mid)
        middiff = midl.symmetric_difference(cl)
        
        if len(middiff) == 0:
            return self.technical_binary_thing(mid, b, accu)
        else:
            return self.technical_binary_thing(a, mid, accu)
            
    # naive binary search for turn that gives good line
    def calculate_next_orientation(self):
        curr = self.orientation
        final = self.wanted_orientation

        if len(self.calculate_line(curr).symmetric_difference(self.calculate_line(final))) == 0:
            self.done = True
            self.orientation = self.wanted_orientation
            self.next_orientation = self.wanted_orientation
            #self.next_line = self.calculate_line(self.next_orientation)
            self.current_line = self.wanted_line
            self.next_line = self.wanted_line
            return
        
        # naively pick rotation direction based on distance
        # I do not know if it's correct, but presumably close enough
        for k in [self.wanted_orientation - 3, self.wanted_orientation + 3]:
            if abs(k - curr) < abs(final - curr):
                final = k

        if final > curr:
            inc = 1
        else:
            inc = -1
        self.techno_counter = 0
        self.next_orientation = self.technical_binary_thing(curr, curr + rat(inc, self.size))
        #print(self.orientation, self.next_orientation, self.techno_counter)
        self.calculate_next_line()

    def calculate_next_line(self):
        self.next_line = self.calculate_line(self.next_orientation)

    def set_wanted_orientation(self, ori):
        ori = rat(ori, 1)
        self.wanted_orientation = ori
        self.wanted_line = self.calculate_line(ori)
        #print(self.current_line, "ami")
        #print(self.final_line)
        self.timer = 0
        self.done = False

        if self.wanted_line == self.current_line:
            self.done = True
            self.set_orientation(self.wanted_orientation)
        self.calculate_next_orientation()

    # def self.pretend_orientation = self.current_orientation
            
    def set_merge_orientation_from_pt(self, side, pt):
        a, b = side_to_endpoints_cw(side)
        #print("side to end", side, a, b)
        av, bv = self.corners[a], self.corners[b]
        at = unlerp(pt, av, bv)
        #print(at, "is where it's at", (side + at) % 3)
        self.set_wanted_orientation((side + at) % 3)
        #print(self.corners[0], "wante", self.wanted_orientation)
            
    # rotate line; there should be a triangle move whenever sum of steps passes an integer
    # we should rotate line, change our current dots, and
    # also send back a list of triangle moves (it's always going to be a singleton or empty in this implementation)
    def update_orientation(self, step):
        #print("mkiliman")
        self.timer += step
        if self.done == True:
            return []

        moves = []
        
        while self.timer >= 1:
            #print("timor")
            self.timer -= 1
            
            if self.orientation != self.next_orientation:
                cl = self.current_line
                nl = self.next_line
                sd = cl.symmetric_difference(nl)
                sd = list(sd)
                if len(sd) == 0:
                    assert self.done
                    return []
                assert len(sd) == 2
                if sd[0] not in self.current_line:
                    sd = [sd[1], sd[0]]
                moves.append(sd)

            self.set_orientation(self.next_orientation)
            self.calculate_current_line()
            self.calculate_next_orientation()
        self.pretend_orientation = slerp(self.timer, self.orientation, self.next_orientation)
        
        return moves

    def calculate_current_line(self):
        #print("calculating curne", self.orientation, repr(self.orientation))
        self.current_line = self.calculate_line(self.orientation)

    # size and this particular'th corner should be correct,
    # then calculate other corners
    def calculate_corners_from_one(self, corner):
        s = self.size - 1
        if corner == 0:
            self.corners[1] = vadd(self.corners[0], (0, s))
            self.corners[2] = vadd(self.corners[0], (s, 0))
        if corner == 1:
            self.corners[0] = vadd(self.corners[1], (0, -s))
            self.corners[2] = vadd(self.corners[1], (s, -s))
        if corner == 2:
            self.corners[0] = vadd(self.corners[2], (-s, 0))
            self.corners[1] = vadd(self.corners[2], (-s, s))

    def reorientation_done(self):
        return self.done

    def normalization_generator(self):
        self.current_height = None
        self.top_excess = None

        # move the xth column right
        for x in range(self.size - 1):
            #print(f"dealing with x = {x}")
            self.height_of_current_column = self.size - 1 - x # discounting the bottom line
            
            # start up
            # if x = 0, we are in the leftmost column, so height of column is size
            # size-1 guys need to be moved, starting from topmost
            self.dropped_count = 0
            for y in range(self.size - x):
                #print(f"dealing with y = {y}, basic drop")
                #print(x, y, "going")
                self.move_down_instead = False
                if y == self.size - x - 1:
                    self.move_down_instead = True
                if vadd(self.corners[0], (x + 1, y)) in self.dots:
                    self.move_down_instead = True
                if not self.move_down_instead:
                    # first we move the top bottom right
                    a = (x, y)
                    b = (x + 1, y)
                    yield [(a, b)]
                else:
                    for z in reversed(list(range(self.dropped_count, y))):
                        yield [((x, z+1), (x, z))]
                        
                    self.dropped_count += 1
            #print("basic drop finished")

            self.dropped_count -= 1

            if x == 0:
                self.current_height = self.dropped_count
                self.top_excess = 0
                
            else:
                if self.dropped_count < self.current_height:

                    while self.dropped_count < self.current_height:

                        if self.current_height <= self.height_of_current_column:

                            #print(f"in the loop: dc {self.dropped_count}, ch {self.current_height}, te {self.top_excess}")
                            if self.dropped_count < self.current_height - 1:
                                
                                if self.top_excess > 0:
                                    for z in range(self.top_excess-1, x-2):
                                        yield [((z+1, self.current_height), (z+1, self.current_height+1)),
                                               ((z, self.current_height+1), (z+1, self.current_height))]
                                
                                    yield [((x-1, self.current_height), (x, self.current_height-1))]
                                    yield [((x-2, self.current_height+1), (x-1, self.current_height))]
                                    for y in reversed(list(range(self.dropped_count+1, self.current_height-1))):
                                        yield [((x, y+1), (x, y))]

                                    self.top_excess -= 1

                                else:

                                    yield [((x-1, self.current_height), (x, self.current_height-1))]
                                    for y in reversed(list(range(self.dropped_count+1, self.current_height-1))):
                                        yield [((x, y+1), (x, y))]
                                    #print("case A")
                                    self.top_excess = x-1
                                    self.current_height -= 1


                            else: # difference is 1!!!

                                if self.top_excess > 0:
                                    #print("heresadf")
                                    for z in range(self.top_excess-1, x-2):
                                        yield [((z+1, self.current_height), (z+1, self.current_height+1)),
                                               ((z, self.current_height+1), (z+1, self.current_height))]

                                    yield [((x, self.current_height-1), (x, self.current_height))]
                                    yield [((x-1, self.current_height), (x, self.current_height-1))]
                                    yield [((x-2, self.current_height+1), (x-1, self.current_height))]

                                    self.top_excess -= 1

                                else: # top excess = 0
                                    #print("case B")
                                    self.top_excess = x
                                    self.current_height -= 1
                                    
                            self.dropped_count += 1
                                    
                        elif self.dropped_count < self.height_of_current_column:
                            # self.dropped_count < self.current_height AND
                            # self.current_height > self.height_of_current_column <-- really just this
                            ell = self.size - (self.current_height + 1) # length of excess row
                            if self.top_excess > 0:
                                # step 1: move excess horizontally
                                # use coordinate of destination

                                # final destination = (ell-1, self.current_height+1)
                                for xx in range(self.top_excess, ell):
                                    yield [((xx, self.current_height), (xx, self.current_height+1)),
                                           ((xx-1, self.current_height+1), (xx, self.current_height))]
                                    
                                # step 2: move stuff diagonally
                                # coord of lowest destination (x, self.height_of_current_column)
                                # coord of topmost is (ell, self.current_height)
                                num_steps = self.current_height - self.height_of_current_column + 1
                                for i in range(num_steps):
                                    yield [((x-1-i, self.height_of_current_column+1+i), (x-i, self.height_of_current_column+i))]
                                self.top_excess -= 1

                            else:
                                num_steps = self.current_height - self.height_of_current_column
                                for i in range(num_steps):
                                    yield [((x-1-i, self.height_of_current_column+1+i), (x-i, self.height_of_current_column+i))]

                                self.current_height -= 1
                                self.top_excess = ell

                            # step 3: drop stuff
                            # we have dot at (x, hocc), need to move to (x, self.dropped_count+1)
                            for y in reversed(list(range(self.dropped_count+1, self.height_of_current_column))):
                                yield [((x, y+1), (x, y))]
                            
                            self.dropped_count += 1

                        else:
                            break
                                
                                
                            
                    
                else: # self.dropped_count >= self.current_height:
                    
                    while self.dropped_count > self.current_height:
                        yield [((x, self.current_height), (x-1, self.current_height+1))]
                        for y in range(self.current_height, self.dropped_count):
                            yield [((x, y+1), (x, y))]
                        self.dropped_count -= 1

                        for xx in reversed(list(range(self.top_excess, x-1))):
                            yield [((xx+1, self.current_height), (xx, self.current_height+1)),
                                   ((xx+1, self.current_height+1), (xx+1, self.current_height))]

                        self.top_excess += 1
                        #print(f"moment {self.top_excess}")
                        if self.top_excess == x and self.dropped_count > self.current_height:
                            self.top_excess = 0
                            self.current_height += 1
                        

        self.normalized = True
        self.set_orientation(0)
        while True:
            yield []

    def start_normalization(self):
        self.normalization_phase = ORIENT
        self.set_wanted_orientation(2)
        self.normalized = False

    def update_normalization(self, step):
        if self.normalization_phase == ORIENT:
            upd = self.update_orientation(step)
            if self.reorientation_done():
                self.normalization_phase = FALL
                self.normafun = self.normalization_generator()
            return upd
        else:
            #self.normalized = True
            self.timer += step
            upds = []
            while self.timer >= 1:
                self.timer -= 1
                ext = next(self.normafun)
                for k in ext:
                    upds.append(tuple(map(lambda a:vadd(self.corners[0], a), k)))
                #print(f"current height {self.current_height}; top_excess {self.top_excess}; dropped_count {self.dropped_count}")
                
            #print(upds)
            return upds

    def normalization_done(self):
        return self.normalized

    

def merge_triangles(tri1, tri2):
    assert tri1.done and tri2.done
    flip, side = tri1.neighbor_side(tri2)
    if flip:
        return merge_triangles(tri2, tri1)
    # get lines for assertion purposes
    lines1 = tri1.current_line
    lines2 = tri2.current_line

    #print("MERGE FINISH")
    #print(tri1.corners, tri1.orientation)
    #print(tri2.corners, tri2.orientation)
    
    # now tri1 should be made larger by size of tri2, in direction side
    t = Triangle((0, 0), tri1.dots) # (0, 0) is cuz don't matter
    t.size = tri1.size + tri2.size
    t.set_orientation(tri1.orientation)
    if tri1.size > 1 and tri2.size > 1:
        assert tri1.orientation == tri2.orientation
    opposite_point = 2 - side
    t.corners = [None, None, None]
    t.corners[opposite_point] = tri1.corners[opposite_point]
    t.calculate_corners_from_one(2 - side)
    t.calculate_current_line()

    #print(t.corners, t.orientation, "result")
    #print(t.current_line)
    #print(t.calculate_line(t.orientation))

    return t

# scalar lerp
def slerp(t, a, b):
    return a + t*(b - a)

# given p, a, b, calculate (some) t such that p = a + t(b - a)
def unlerp(p, a, b):
    if a[0] == b[0] and a[1] == b[1]:
        assert p == a
        return 0
    if a[0] == b[0]:
        return unlerp((p[1], p[0]), (a[1], a[0]), (b[1], b[0])) # we can do any affine transformation to the triple clearly
    """
    p = a + t(b - a)
    px = ax + t(bx - ax)
    (px - ax)/(bx - ax) = t
    """
    return (p[0] - a[0])/(rat(b[0], 1) - rat(a[0], 1))

def side_to_endpoints_cw(side):
    side = side % 3
    if side == 0:
        return 0, 1
    if side == 1:
        return 2, 0
    if side == 2:
        return 1, 2

def apply_random(dots):
    d = random.choice(list(dots))
    #print(d)
    tri = [(0,0), (1,0), (0,1)]
    idx = random.randint(0, 2)
    tri = set(map(lambda a:vadd(d, vsub(a, tri[idx])), tri))
    tri.remove(d)
    #print(tri)
    tri = list(tri)
    random.shuffle(tri)
    assert len(tri) == 2 and d not in tri
    if tri[0] in dots and tri[1] not in dots:
        #print("did")
        dots.remove(tri[0])
        dots.add(tri[1])
    else:
        #print("sad")
        pass

s = """
10000000
01000000
00000000
11000000
00000000
00000000
00001010
00001001
"""

"""
#random.seed(39)
s = "111111111111111"
dots = from_s(s)
for i in range(100000):
    #print(dots)
    apply_random(dots)
"""

s = """
111111111111111111
1111111111111111111
11111111111111111111
"""


dots = set() #from_s(s)
#for i in range(3000):
#    #print(dots)
#    apply_random(dots)


#s = """
#111
#010
#"""
"""
dots = from_s(s)
tri = Triangle((0, 0), dots)
tri.corners = [(0,0), None, None]
tri.size = 12
tri.calculate_corners_from_one(0)
tri.set_orientation(2)
triangles = set([tri])

"""
def calculate_bounds(dots):
    left = None
    bottom = None
    for d in dots:
        if left == None or d[0] < left:
            left = d[0]
        if bottom == None or d[1] < bottom:
            bottom = d[1]
    size = 0
    for d in dots:
        if sum(d) - left > size:
            size = sum(d) - left
        if sum(d) - bottom > size:
            size = sum(d) - bottom
    return left, bottom, size + 1

#leftbound, bottombound, size = calculate_bounds(dots)
#print(leftbound, bottombound, size)
leftbound = 0
bottombound = 0
size = 20

dots = set(map(lambda a:(rat(a[0], 1), rat(a[1], 1)), dots))
triangles = set(Triangle(v, dots) for v in dots)





#a = bbb
"""
triangles = set()
t1 = Triangle((0,0), dots) # the leftmost
t1.size = 3
t.corners = [(0, 1), (0, 3), ()]
triangles.add()
"""


#t = Triangle((0, 0), [])
#print(t.get_thickened(0.2))

#t = Triangle((0,0), [])

#t.size = 7
#t.line_dots = set([])
#t.corners = [(0,0), (0,7), (7,0)]
# the line is determined by a number [0, 3), 0 1 2 mean left down ne,
# and remainder means dist of endpoint on that side, clockwise
#self.orientation = 0


#print(t.calculate_line(0.083333))
#print(t.calculate_line(0.083334))



#a = bbb

"""
t.orientation = 0
t.calculate_current_line()
t.set_wanted_orientation(1)
t.calculate_next_orientation()

print(t.next_orientation)

a = bbb
"""






"""

# for L grid:

# logical to screen
def to_screen(v):
    return width/2+(v[0] - xpos)*scale, height/2-(v[1] - ypos)*scale

# screen to logical
def to_logical(v):
    return (v[0]-width/2)/scale + xpos, -(v[1]-height/2)/scale + ypos

"""

# for 60 degree grid

# logical to screen
def to_screen(v):
    x = (1, 0)
    y = (math.cos(math.pi/3), -math.sin(math.pi/3))
    scrcenter = (width/2, height/2)
    pos = (xpos, ypos)
    return vadd(scrcenter, smul(scale, vsub(vadd(smul(v[0], x), smul(v[1], y)), pos)))

# screen to logical
# you can use this for any
def to_logical(v):
    scrcenter = (width/2, height/2)
    pos = (xpos, ypos)
    v = vsub(v, scrcenter)
    # now v = smul(scale, vsub(vadd(smul(v[0], x), smul(v[1], y)), pos))
    v = smul(1/scale, v)
    # now v = vsub(vadd(smul(v[0], x), smul(v[1], y)), pos)
    v = vadd(v, pos)
    # now v = vadd(smul(v[0], x), smul(v[1], y))
    
    y = (math.cos(math.pi/3), -math.sin(math.pi/3))
    # easy to figure out how many y's are in v
    yinv = v[1]/y[1]
    # erase the contribution
    v = vsub(v, smul(yinv, y))
    # now it's easy to figure out the x's
    return rat(v[0]), rat(yinv)


# check that we can move from a to b
def pivot_exists(dots, a, b):
    if b == vadd(a, (0, 1)):
        return vadd(a, (1, 0)) in dots
    if b == vadd(a, (1, 0)):
        return vadd(a, (0, 1)) in dots
    if b == vadd(a, (0, -1)):
        return vadd(a, (1, -1)) in dots
    if b == vadd(a, (1, -1)):
        return vadd(a, (0, -1)) in dots
    if b == vadd(a, (-1, 0)):
        return vadd(a, (-1, 1)) in dots
    if b == vadd(a, (-1, 1)):
        return vadd(a, (-1, 0)) in dots

# given logical position, find nearest lattice point, assuming grid is reasonably non-distorted...
def nearest_logical(pos):
    discrete = int(pos[0]), int(pos[1])
    nearest = None
    nearest_dist = None
    for x in range(-5, 6):
        for y in range(-5, 6):
            v = vadd(discrete, (x, y))
            dist = sqrdist(to_screen(v), to_screen(pos))
            if nearest == None or nearest_dist > dist:
                nearest_dist = dist
                nearest = v
    return nearest

def is_in_area(vec):
    x,y = vec
    if not x in range(leftbound, leftbound + size):
        return False
    if not y in range(bottombound, bottombound + size):
        return False
    if (x-leftbound) + (y-bottombound) > size - 1:
        return False
    return True

def main():

    global chosentriangle, xpos, ypos, scale, speed, triangles, dots
    
    # Initialise screen
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('Basic Pygame program')

    # Fill background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((250, 250, 250))

    #font = pygame.font.SysFont('system', 36)
    font = pygame.font.SysFont('arial', 36)

    # Blit everything to the screen
    screen.blit(background, (0, 0))
    pygame.display.flip()

    action = SOLITAIRE
    randomization = False
    random_steps = 1

    # Event loop
    while 1:

        do_a_step = False
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return

            if event.type == pygame.MOUSEBUTTONUP:
                if action == IDLE:
                    clickedtriangle = None
                    pos = pygame.mouse.get_pos()
                    pos = to_logical(pos)
                    for t in triangles:
                        if t.contains(pos, MARGIN):
                            clickedtriangle = t
                    if event.button == 1:
                        if clickedtriangle == None:
                            chosentriangle = None
                        elif chosentriangle == None:
                            chosentriangle = clickedtriangle
                        elif chosentriangle.is_neighbor(clickedtriangle):
                            action = MERGING
                            tri1 = chosentriangle
                            tri2 = clickedtriangle
                            set_merge_orientations(tri1, tri2)
                            #print(tri1.wanted_orientation, "want")
                            #print(tri2.wanted_orientation, "cant")
                        else:
                            chosentriangle = clickedtriangle
                    elif event.button == 3:
                        if clickedtriangle != None:
                            action = NORMALIZE
                            tri1 = clickedtriangle
                            tri1.start_normalization()

            if event.type == pygame.KEYDOWN:
                if event.key == K_SPACE:
                    do_a_step = True
                if event.key == K_1:
                    if action in idles:
                        action = SOLITAIRE
                if event.key == K_2:
                    if action in idles:
                        action = EDITING
                if event.key == K_3:
                    if action in idles:
                        action = IDLE
                        randomization = False
                        
                        dots = set(map(lambda a:(rat(a[0], 1), rat(a[1], 1)), dots))
                        triangles = set(Triangle(v, dots) for v in dots)

                if event.key == K_r and action in [EDITING, SOLITAIRE]:
                    randomization = not randomization

                rotate = 0
                if event.key == K_k:
                    rotate = -1
                if event.key == K_j:
                    rotate = 1

                if event.key == K_t:
                    random_steps *= 2
                if event.key == K_y:
                    if random_steps > 1:
                        random_steps //= 2
                    
                if action == SOLITAIRE and rotate != 0:
                    if moused_triangle != None:
                        a = moused_triangle
                        b = vadd(moused_triangle, (1,0))
                        c = vadd(moused_triangle, (0,1))
                        dems = [a, b, c]
                        bools = []
                        indots_count = 0
                        for k in dems:
                            if k in dots: indots_count += 1
                            bools.append(k in dots)
                        #print(bools, indots_count)
                        if indots_count == 2:
                            if rotate == 1:
                                bools = bools[1:] + bools[:1]
                            else:
                                bools = bools[2:] + bools[:2]
                            #print(bools)
                            for i, k in zip(dems, bools):
                                #print(i, k)
                                if i in dots:
                                    dots.remove(i)
                                if k:
                                    dots.add(i)


        moused_triangle = None
        if action == SOLITAIRE:
            pos = pygame.mouse.get_pos()
            pos = to_logical(pos)
            poso = int(pos[0]), int(pos[1])
            if sum(vsub(pos, poso)) < 1:
                moused_triangle = poso
            #print(pos)

        mpress = pygame.mouse.get_pressed()
        if action == EDITING and (mpress[0] or mpress[2]):
            pos = pygame.mouse.get_pos()
            pos = to_logical(pos)

            vec = nearest_logical(pos)
            
            if mpress[0] and is_in_area(vec):
                dots.add(vec)
            if mpress[2]:
                dots.discard(vec)

        keys = pygame.key.get_pressed()
        if keys[K_UP]:
            ypos -= 0.01
        if keys[K_DOWN]:
            ypos += 0.01
        if keys[K_LEFT]:
            xpos -= 0.01
        if keys[K_RIGHT]:
            xpos += 0.01
        if keys[K_a]:
            scale *= 0.99
        if keys[K_z]:
            scale /= 0.99
        if keys[K_s]:
            speed /= rat(99, 100)
        if keys[K_x]:
            speed *= rat(99, 100)
                        
        # movement

        if (action == SOLITAIRE or action == EDITING) and randomization:
            for r in range(random_steps):
                apply_random(dots)

        updates = []

        if action == MERGING:
            upd1 = tri1.update_orientation(speed)
            upd2 = tri2.update_orientation(speed)
            updates = upd1 + upd2

        if action == KILL:
            for t in killeds:
                updates.extend(t.update_orientation(speed))

        if action == NORMALIZE and (do_a_step or True):
            updates.extend(tri1.update_normalization(speed))

        for m in updates:
            #print(m, "actually")
            if l == []:
                continue
            a, b = m[0], m[1]
            #print(a, "moves to", b)
            assert pivot_exists(dots, a, b)
            assert a in dots
            if a in dots and b in dots:
                continue
            elif b not in dots:
                # could add some animation ofc
                dots.remove(a)
                dots.add(b)

        if action == MERGING:
            if tri1.reorientation_done() and tri2.reorientation_done():
                tri = merge_triangles(tri1, tri2)
                triangles.remove(tri1)
                triangles.remove(tri2)
                triangles.add(tri)

                killeds = []
                for t in triangles:
                    if t != tri:
                        if t.intersects(tri):
                            t.die(tri)
                            killeds.append(t)

                if len(killeds) == 0:
                    action = IDLE
                else:
                    murderer = tri
                    action = KILL
                chosentriangle = None

        elif action == KILL:
            for t in killeds[:]:
                if t.reorientation_done():
                    triangles.update(t.merge_with_murderer(murderer))
                    triangles.remove(t)
                    killeds.remove(t)
            if len(killeds) == 0:
                action = IDLE

        elif action == NORMALIZE:
            if tri1.normalization_done():
                action = IDLE

        # drawing

        screen.blit(background, (0, 0))


        if action == SOLITAIRE and moused_triangle != None:
            mous_phys = to_screen(moused_triangle)
            mous_phys_up = to_screen(vadd(moused_triangle, (0,1)))
            mous_phys_right = to_screen(vadd(moused_triangle, (1,0)))
            # pygame.draw.circle(screen, (0,0,0), mous_phys, 3)
            pygame.draw.line(screen, (150,150,150), mous_phys, mous_phys_up, 1)
            pygame.draw.line(screen, (150,150,150), mous_phys_up, mous_phys_right, 1)
            pygame.draw.line(screen, (150,150,150), mous_phys_right, mous_phys, 1)
            
        for x in range(leftbound, leftbound + size):
            for y in range(bottombound, bottombound + size):
                if (x-leftbound) + (y-bottombound) > size - 1:
                    continue
                r = 1
                if (x, y) in dots: r = 4
                pygame.draw.circle(screen, (0, 0, 0), to_screen((x, y)), r) 


        for t in triangles:
            if action == SOLITAIRE or action == EDITING:
                continue

            ls = t.get_drawn_lines()
            for l in ls:
                pygame.draw.lines(screen, (0, 0, 0), True, list(map(to_screen, l)))
                pass
            
            pts = t.get_thickened(MARGIN)
            color = (0, 0, 0)
            if action == IDLE:
                if chosentriangle == t:
                    color = (255, 0, 0)
                elif chosentriangle and chosentriangle.is_neighbor(t):
                    color = (0, 255, 0)
            elif action == MERGING:
                if tri1 == t or tri2 == t:
                    color = (0, 0, 255)
                    
            pygame.draw.lines(screen, color, True, list(map(to_screen, pts)))

        def texty(xx, yy, tex):
            text = font.render(tex, 1, (10, 10, 10))
            textpos = text.get_rect()
            textpos.left = xx #background.get_rect().centerx
            textpos.top = yy
            screen.blit(text, textpos)
        

        ddd = {IDLE : "semiautoplay",
               MERGING : "merging...",
               KILL : "cutting...",
               NORMALIZE : "normalizing...",
               EDITING : "editing",
               SOLITAIRE : "solitaire"}

        texty(30, 30, f'mode = {ddd[action]}')
        texty(30, 60, f"random steps = {random_steps}")
        texty(30, 90, f'speed = {float(speed):.4f}')

    
        pygame.display.flip()


if __name__ == '__main__': main()









