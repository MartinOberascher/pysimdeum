from traits.api import HasStrictTraits, Bool, Any, Str, Either, Instance
import copy
import numpy as np
import scipy.stats as ss
import pandas as pd
import uuid
from pySIMDEUM.core.utils import Base


class Presence(HasStrictTraits):

    weekday = Bool
    user = Any

    up = Instance(pd.Timedelta)
    go = Instance(pd.Timedelta)
    home = Instance(pd.Timedelta)
    sleep = Instance(pd.Timedelta)

    _prob_getting_up = Any
    _prob_leaving_house = Any
    _prob_being_away = Any
    _prob_sleep = Any

    def __init__(self, user=None, weekday=True, stats=None):

        super(Presence, self).__init__()

        self.user = user

        if weekday:
            diurnal = copy.deepcopy(stats.diurnal_pattern[user.age])
        else:
            diurnal = copy.deepcopy(stats.diurnal_pattern['weekend'])

        for key, val in diurnal.items():
            dist = val['dist']
            del val['dist']
            # dist = getattr(pm, dist)
            dist = getattr(ss, dist)
            newval = dict()
            translate = {'mu': 'loc',
                         'sd': 'scale'}

            for x, y in val.items():
                newval[translate[x]] = round(pd.Timedelta(y).total_seconds() / 60)

            # setattr(self, '_prob_' + key, dist.dist(**newval))
            setattr(self, '_prob_' + key, dist(**newval))

        self.up = self.sample_single_property('_prob_getting_up')

        self.sleep = self.up - self.sample_single_property('_prob_sleep') + pd.Timedelta(days=1)

        self.go = self.sample_single_property('_prob_leaving_house')

        if self.go < self.up:
            self.go = self.up + pd.Timedelta(minutes=30)

        self.home = self.go + self.sample_single_property('_prob_being_away')

        if self.home < self.go:
            self.home = self.go  # actually no leave

        if self.sleep < self.home:
            self.home = self.sleep - pd.Timedelta(minutes=30)

    def print(self):
        print('up:', self.up)
        print('go:', self.go)
        print('home:', self.home)
        print('sleep:', self.sleep)

    def sample_single_property(self, prop):

        prob_fct = getattr(self, prop)
        x = prob_fct.rvs()
        x = int(np.round(x))
        x = pd.Timedelta(minutes=x)
        return x

    @staticmethod
    def timestamp2str(x):
        return str(x.components.hours).zfill(2) + ':' + str(x.components.minutes).zfill(2) # + ':' + str(
        # x.components.seconds).zfill(2)

    def timeindexer(self, l, value, a, b):
        if a < b:
            l[a:b] = value
        else:
            l[a:len(l)] = value
            l[0:b] = value
        return l

    def pdf(self, peak=0.65, normal=0.335, away=0.0, night=0.015):
        index = pd.timedelta_range(start='00:00:00', end='24:00:00', freq='1Min')
        pdf = pd.Series(index=index)

        up = int((self.up.total_seconds()) / 60) % 1440
        up_p30 = int((up + 30)) % 1440

        go = int(self.go.total_seconds() / 60) % 1440
        go_m30 = int(go - 30) % 1440

        home = int(self.home.total_seconds() / 60) % 1440
        home_p30 = int(home + 30) % 1440

        sleep = int(self.sleep.total_seconds() / 60) % 1440
        sleep_m30 = int(sleep - 30) % 1440

        pdf = self.timeindexer(pdf, 'normal', up_p30, go_m30)
        pdf = self.timeindexer(pdf, 'normal', home_p30, sleep_m30)
        pdf = self.timeindexer(pdf, 'peak', up, up_p30)
        pdf = self.timeindexer(pdf, 'peak', go_m30, go)
        pdf = self.timeindexer(pdf, 'peak', home, home_p30)
        pdf = self.timeindexer(pdf, 'peak', sleep_m30, sleep)
        pdf = self.timeindexer(pdf, 'night', sleep, up)
        pdf = self.timeindexer(pdf, 'away', go, home)

        cnts = pdf.value_counts(normalize=True)
        try:
            cnts = cnts.drop('away')
        except:
            pass
        cnts /= cnts.sum()
        try:
            pdf[pdf == 'peak'] = peak / cnts['peak']
        except:
            pass
        try:
            pdf[pdf == 'normal'] = normal / cnts['normal']
        except:
            pass
        try:
            pdf[pdf == 'night'] = night / cnts['night']
        except:
            pass
        try:
            pdf[pdf == 'away'] = 0.0
        except:
            pass


        pdf = pdf.astype('float').resample('1S').fillna('ffill')[:-1]

        pdf /= np.sum(pdf)  # normalize

        # transform timedeltas to strings for indexing later on
        return pdf


class User(Base):

    id = Str
    house = Any
    gender = Either(None, 'male', 'female')
    age = Either('child', 'teen', 'home_ad', 'work_ad', 'senior')
    presence = Any
    consumption = Instance(pd.Series)

    def __init__(self, id=None, age=None, gender=None, house=None, job=True):

        super(User, self).__init__(id=id)

        self.gender = gender
        self.house = house

        if id is None:
            id = str(uuid.uuid4())
        self.id = id

        if age == 'adult':
            if job:
                self.age = 'work_ad'
            else:
                self.age = 'home_ad'
        else:
            self.age = age

    def compute_presence(self, weekday=True, statistics=None, peak=0.65, normal=0.335, away=0.0, night=0.15):

        presence = Presence(user=self, weekday=weekday, stats=statistics)
        pdf = presence.pdf(peak=peak, normal=normal, away=away, night=night)
        self.presence = pdf

        return self.presence