# Module: feature_generator.py
# This module can 1) load a package, 2) generate features for the models, and 3) create a single feature series for model scoring

import pandas as pd
import numpy as np
from scipy.fftpack import fft, ifft
from scipy import signal
from scipy.signal import butter, lfilter, freqz
from scipy.stats import skew


def load_files(filename):
    df = pd.read_csv(filename, sep=",", skiprows=3, skipinitialspace=False)
    df.columns = ['Time','X', 'Y', 'Z', 'R', 'Theta', 'Phi']
    return df


class generateFeatures:
    """Define methods that pre-process raw measurement dataframe, including filtering*, detrending and generating features"""
    
    def __init__(self, df, load='Under Load', metric='X', smooth = False):
        self.df = df
        self.load = load.replace(" ", "")
        self.metric = metric
        self.smooth = smooth
        
    def timeTrim(self, lo=2, hi=1):
        """remove first two seconds and final second"""
        if max(self.df['Time']) > lo+hi:
            self.df = self.df[(self.df['Time'] >= lo) & (self.df['Time'] <= max(self.df['Time'])-hi)]
        
    def lowFilter(self, args):
        """apply low-pass filter; see Adam's work. this is somewhat handled in the cutoff argument to maxFFT below"""
        pass
    
    def getSmoothed(self, window_len=10, window = 'flat'):
        """smooth the data using a window with requested size"""
        """modified from https://scipy-cookbook.readthedocs.io/items/SignalSmooth.html"""
        if self.smooth == False:
            pass
        else:
            data = []
            for dim in self.df:

                s = np.r_[self.df[dim][window_len-1:0:-1],self.df[dim],self.df[dim][-2:-window_len-1:-1]]

                if window == 'flat': # moving average
                    w = np.ones(window_len,'d')
                else:
                    w = eval('np.'+window+'(window_len)')

                y = np.convolve(w/w.sum(),s,mode='valid')
                data.append(pd.Series(y, name=dim))
            self.smoothed = pd.concat(data, axis=1)
            self.smooth = True
    
    def getDetrended(self):
        """center about zero without linear time trend (uses smoothed signal if available)"""
        if self.smooth: 
            self.detrended = self.smoothed.copy()
            self.detrended[self.metric] = signal.detrend(self.smoothed[self.metric])
            self.length = self.detrended.shape[0]
        else:
            self.detrended = self.df.copy()
            self.detrended[self.metric] = signal.detrend(self.df[self.metric])
            self.length = self.detrended.shape[0]
        
    def getPower(self):
        """average squared amplitude value"""
        return pd.Series(sum(np.square(self.detrended[self.metric]))/self.length,
                         [self.load+'_'+self.metric+'_pwr'])
    
    def getAvg(self):
        """mean amplitude, similar to power"""
        """IGNORE: detrend normalizes the mean to zero using regression"""
        self.mean = np.mean(self.detrended[self.metric])
        return pd.Series(self.mean, [self.load+'_'+self.metric+'_avg'])
    
    def getStdDev(self):
        """standard deviation of amplitudes"""
        """from literature, this feature is OK"""
        return pd.Series(np.std(self.detrended[self.metric]), [self.load+'_'+self.metric+'_std'])
    
    def getSkew(self):
        """3rd order feature, strong predictor in Ruiz et al"""
        self.skew = skew(self.detrended[self.metric])
        return pd.Series(self.skew, [self.load+'_'+self.metric+'_skew'])
        
    
    def getFFT(self):
        """perform Fast Fourier transformation of metric series"""
        self.N = self.detrended.shape[0]
        # sample spacing
        T = 0.005
        self.freq = np.linspace(0.0, 1.0/(2.0*T), self.N//2)
        rawFFT = fft(self.detrended[self.metric])
        self.fft_values = 2.0/self.N * np.abs(rawFFT[:self.N//2])
    
    def maxFFT(self, cutoff=.1):
        """get the pair of max FFT value and frequency"""
        start = int(cutoff*(self.fft_values.shape[0]))
        maxFFT = np.max(self.fft_values[start:])
        maxFreq = self.freq[start+np.argmax(self.fft_values[start:])]
        #return (maxFFT, maxFreq)
        return pd.Series([maxFFT, maxFreq], [self.load+'_'+self.metric+'_maxFFT', self.load+'_'+self.metric+'_maxFreq'])
    
    def meanLowFFT(self, minFreq=15, maxFreq=65, name='avgFFT'):
        """mean FFT_value is greater for broken derailleur cog when above a frequency of ~65 for X 'Under Load'"""
        if (self.load == 'UnderLoad'):
            mean = np.mean(self.fft_values[(self.freq >= minFreq) & (self.freq <= maxFreq)])
            return pd.Series(mean, [self.load+'_'+self.metric+'_'+name])
        
    def derailleur(self, minFreq=65, maxFreq=100, name='dCog'):
        """avg FFT_value is greater for broken derailleur cog when above a frequency of ~65 for X 'Under Load'"""
        if (self.metric == 'X') & (self.load == 'UnderLoad'):
            mean = np.mean(self.fft_values[(self.freq >= minFreq) & (self.freq <= maxFreq)])
            return pd.Series(mean, [self.load+'_'+self.metric+'_'+name])
    
    def chain(self, minFreq=60, maxFreq=100, name='chain'):
        """avg FFT_value is greater with chain issues when above a frequency of ~60 for Z 'Under Load'"""
        if (self.metric == 'Z') & (self.load == 'UnderLoad'):
            mean = np.mean(self.fft_values[(self.freq >= minFreq) & (self.freq <= maxFreq)])
            return pd.Series(mean, [self.load+'_'+self.metric+'_'+name])
    
    def braking(self, minFreq=15, maxFreq=40, name='brake'):
        """avg FFT_value is greater with braking issues at lower frequencies"""
        if (self.metric == 'Z') & (self.load == 'Freewheel+break'):
            mean = np.mean(self.fft_values[(self.freq >= minFreq) & (self.freq <= maxFreq)])
            return pd.Series(mean, [self.load+'_'+self.metric+'_'+name])


def maxSplit(bikeID_files, max_time = 6, max_splits = 100, verbose=False):
    # search through all files for a given BikeID and determine the maximum
    # amount of splits we can generate (default ten seconds)
    max_num = max_time / 0.005
    for filename in bikeID_files:
        sample = load_files('data/'+filename)
        if max_num > sample.Time.count():
            sample_splits = 1.0
        else:
            sample_splits = sample.Time.count() // max_num
        if sample_splits < max_splits:
            max_splits = int(sample_splits)

    if verbose:
        print('Max number of time splits: ', max_splits)
    return max_splits


def singleRowTransform(readingDF, featureRow, action = 'Under Load', metrics = ['X','Y','Z'], smooth=False):
    """input raw text reading and return a Panda series in model-input format for scoring"""
    """for scoring, featureRow should be passed as an empty Panda series"""
    
    for metric in metrics:
        featGenerator = generateFeatures(readingDF, action, metric, smooth)
        featGenerator.getSmoothed() # comment out if not using a smoothing function; updated: handled by getSmoothed if-else
        featGenerator.getDetrended()
        featGenerator.getFFT()
        featureRow = featureRow.append([featGenerator.getPower(), 
                                        featGenerator.getStdDev(), 
                                        featGenerator.getSkew(),
                                        featGenerator.maxFFT(), 
                                        #featGenerator.meanLowFFT(),
                                        featGenerator.derailleur(), 
                                        featGenerator.chain()]
                                        #featGenerator.braking()]
                                      )
    return featureRow
    
    
    