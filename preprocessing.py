from mne.utils import verbose, logger
from mne.filter import resample
import numpy as np
import numpy.fft as fft_pack
from scipy.stats import zscore
import scipy.io
import pyfftw
#import hdf5storage
#from spectrum import pmtm
import matlab
from ez_detect.config import TEMPORARY_DUE_TRANSLATION

def _impedance_check(eeg_data):
    logger.info('Performing impedance check.')
    fifty_cycle=[]
    for j in range(len(eeg_data)):
        logger.info(j)
        channel = eeg_data[j]
        transformedSignal = pyfftw.interfaces.numpy_fft.fft(channel) #Fast Fourier transform 
        frequencyVector = 2000/2 * np.linspace(0, 1, int(len(channel)/2) + 1 )
        powerSpectrum = transformedSignal * np.conj(transformedSignal) / len(channel)
        if j == 0 :
            indexes_1 = np.where(frequencyVector>48)[0] # 50 Hz range starts at 48 Hz
            indexes_2 = np.where(frequencyVector<52)[0] # 50 Hz range ends at 52 Hz
            indexes = np.intersect1d(indexes_1, indexes_2)
            start_index=min(indexes)
            end_index=max(indexes)
        fifty_cycle.append( sum(np.real(powerSpectrum[start_index:end_index+1])) )
    fifty_cycle = np.array(fifty_cycle)
    zfifty_cycle = zscore(fifty_cycle)
    imp_1 = np.where(fifty_cycle>1e9)[0]
    imp_2 = np.where(zfifty_cycle>0.3)[0]
    return set(list(np.intersect1d(imp_1, imp_2)))

def ez_lfbad(eeg_data, ch_names, metadata, matlab_session):

    logger.info('Entering ez_lfbad')

    montage = metadata['montage']
    data = dict()
    ch_ids = np.array( list(montage.sug_as_ref), dtype=int)
    imp = _impedance_check(eeg_data[ ch_ids ])
    if len(imp) > 0:
        imp = list(imp)
        ch_ids = np.delete(ch_ids,imp)
    data['mp_channels'] = eeg_data[ ch_ids ] 
    metadata['ch_names_mp'] = [montage.name(ch_id) for ch_id in ch_ids]

    ch_ids = np.array( list(montage.sug_as_bp), dtype=int)
    pairs = np.array( [ montage.pair_references[ch_id] for ch_id in ch_ids ], dtype=int)
    data['bp_channels'] = eeg_data[ ch_ids ] - eeg_data [ pairs ]
    metadata['ch_names_bp'] = [montage.name(ch_id) for ch_id in ch_ids]
    
    #The list below, includes all the channels that support bipolar montage
    #and that are not filtered by impedance function 
    #(User may have suggested as ref but provided a pair for the case 
    #ez-detect needs to move it to bipolar montage)
    ch_ids = np.array( list( set(montage.pair_references.keys())), dtype=int )
    pairs = np.array( [ montage.pair_references[ch_id] for ch_id in ch_ids ], dtype=int )
    support_bipolar = eeg_data[ ch_ids ] - eeg_data [ pairs ]
    
    args_fname = TEMPORARY_DUE_TRANSLATION +metadata['file_block']+'.mat' 
    scipy.io.savemat(args_fname, dict(data=data, support_bipolar= support_bipolar, file_id=metadata['file_id'], n_blocks=metadata['n_blocks'], block_size=metadata['block_size'], srate=metadata['srate'], file_block=metadata['file_block'], ch_names_bp=metadata['ch_names_bp'], ch_names_mp=metadata['ch_names_mp'], chanlist= ch_names, ez_montage=metadata['old_montage']))
    print("data written")
    #scipy.io.savemat(args_fname, dict(data=data, support_bipolar= support_bipolar, metadata=metadata, chanlist= ch_names, ez_montage=metadata['old_montage']))
    logger.info('about to enter matlab')
    data, metadata = matlab_session.ez_bad_channel_temp(args_fname, nargout=2)
    logger.info('out of matlab')
    
    #data, metadata = _bad_channels_nn(data, metadatam ch_names, support_bipolar)
    #metadata['montage'] = montage
    return data, metadata

def ez_lfbad_lfp(eeg_data, ch_names, metadata, matlab_session):

    logger.info('Entering ez_lfbad')

#   imp = _impedance_check(eeg_data)
    montage = metadata['montage']

    data = dict()
    ch_ids = np.array( list(montage.sug_as_ref), dtype=int)
    data['mp_channels'] = eeg_data[ ch_ids ] 
    metadata['ch_names_mp'] = [montage.name(ch_id) for ch_id in ch_ids]

    ch_ids = np.array( list(montage.sug_as_bp), dtype=int)
    pairs = np.array( [ montage.pair_references[ch_id] for ch_id in ch_ids ], dtype=int)
    #import pdb; pdb.set_trace()
    data['bp_channels'] = eeg_data[ ch_ids ] - eeg_data [ pairs ]
    metadata['ch_names_bp'] = [montage.name(ch_id) for ch_id in ch_ids]
    
    #The list below, includes all the channels that support bipolar montage
    #and that are not filtered by impedance function 
    #(User may have suggested as ref but provided a pair for the case 
    #ez-detect needs to move it to bipolar montage)
    ch_ids = np.array( list( set(montage.pair_references.keys())), dtype=int )
    pairs = np.array( [ montage.pair_references[ch_id] for ch_id in ch_ids ], dtype=int )
    support_bipolar = eeg_data[ ch_ids ] - eeg_data [ pairs ]
    
    args_fname = TEMPORARY_DUE_TRANSLATION +metadata['file_block']+'.mat' 
    scipy.io.savemat(args_fname, dict(data=data, support_bipolar= support_bipolar, file_id=metadata['file_id'], n_blocks=metadata['n_blocks'], block_size=metadata['block_size'], srate=metadata['srate'], file_block=metadata['file_block'], ch_names_bp=metadata['ch_names_bp'], ch_names_mp=metadata['ch_names_mp'], chanlist= ch_names, ez_montage=metadata['old_montage']))
    print("data written")
    #scipy.io.savemat(args_fname, dict(data=data, support_bipolar= support_bipolar, metadata=metadata, chanlist= ch_names, ez_montage=metadata['old_montage']))
    logger.info('about to enter matlab')
    data, metadata = matlab_session.ez_bad_channel_temp_lfp(args_fname, nargout=2)
    logger.info('out of matlab')
    
    #data, metadata = _bad_channels_nn(data, metadatam ch_names, support_bipolar)
    #metadata['montage'] = montage
    return data, metadata

def _clustering_coef_wd(W):
    A = W != 0                                      #adjacency matrix
    S = pow(W, 1/3 ) + pow( np.transpose(W), 1/3)   #symmetrized weights matrix ^1/3
    K = np.sum( A+ np.transpose(A), axis = 1)       #total degree (in + out)
    cyc3 = np.diag(pow(S,3))/2                      #number of 3-cycles (ie. directed triangles)
    K[ cyc3 == 0] = np.inf                          #if no 3-cycles exist, make C=0 (via K=inf)
    CYC3 = K*(K-1) - 2 * np.diag(pow(A,2))          #number of all possible 3-cycles
    C = cyc3 / CYC3;                                #clustering coefficient

def _wentropy(P):   
    return -sum([pow(pi,2) * np.log(pow(pi,2)) for pi in P ])

#translating WIP
'''
def _bad_channels_nn(data, metadata, ch_names, support_bipolar):

    logger.info('Running neural network to find bad electrode recording sites')
    nnetworkin = np.zeros( (len(support_bipolar), 11) ) 
    R = np.corrcoef(support_bipolar)
    CC = abs(R)
    ccwd = _clustering_coef_wd(CC)
    nnetworkin[0] = np.array([ccwd]);
    nnetworkin(1) = np.array([zscore(ccwd)])
    for ii in range(len(support_bipolar)):
        nnetworkin[ii, 2] = _wentropy(support_bipolar[ii])

        # ESTO ES LO QUE FALTA TRADUCIR
        # POWER SPECTRUM DENSITY (MULTITAPER)
        Fs_ds = 1000
        support_bipolar = resample(support_bipolar, down= metadata['srate']/100)  #Downsample to 100 Hz 
        [pxx f] = pmtm(eeg,80,[],Fs_ds);                    % Power Spectrum
        pxx = pxx.';
        pxxAll_train{1,1} = pxx;
          
        % GENERATE TRAINING ARRAY DATA
        logpxx = log10(pxx(:,f>=1 & f<= 500));
        logf = log10(f(f>=1 & f<= 500)); % really 0.2-50 Hz (a.a)
        logpxx1 = log10(pxx(:, f>= 1 & f<=8)); % really 0.2-1.6 Hz
        logpxx2 = log10(pxx(:, f>=1 & f<=16,:)); % really 0.2-3.2 Hz
        logpxx3 = log10(pxx(:, f>= 16 & f<=500)); % really 3.2-50 Hz (a.a)
        logf1 = log10(f(f >= 1 & f <= 8));
        logf2 = log10(f(f >= 1 & f <= 16));
        logf3 = log10(f(f >= 16 & f<=500));
        
        for ch_idx in range( len(support_bipolar)):
        # GENERATE LINEAR FITS FOR LOGLOG POWERSPECTRUM FOR REQUISIT BANDS
            mdl0 = fitlm(logf,logpxx(ch_idx,:));
            mdl1 = fitlm(logf1, logpxx1(ch_idx,:));
            mdl2 = fitlm(logf2, logpxx2(ch_idx,:));
            mdl3 = fitlm(logf3, logpxx3(ch_idx,:));

            nnetworkin(ch_idx,4:5) = [mdl0.Rsquared.Ordinary mdl0.Coefficients.Estimate(2,1)] ;
            nnetworkin(ch_idx,6:7) = [mdl1.Rsquared.Ordinary mdl1.Coefficients.Estimate(2,1)] ;
            nnetworkin(ch_idx,8:9) = [mdl2.Rsquared.Ordinary mdl2.Coefficients.Estimate(2,1)] ;
            nnetworkin(ch_idx,10:11) = [mdl3.Rsquared.Ordinary mdl3.Coefficients.Estimate(2,1)] ;
        #ESTO ES LO QUE FALTA TRADUCIR FIN

        ## Running neural network
        Y = MATLAB.badchannel_nn(nnetworkin)
        a = np.where(Y>0.32)[0]

        metadata['lf_bad'] = np.array(ch_names)[a]
        _, IA, _ = np.intersect1d(metadata['ch_names_bp'], lf_bad, return_indices = True )
        data['bp_channels'] = np.delete(data['bp_channels'], IA) 
        metadata['ch_names_bp'] = np.delete(metadata['ch_names_bp'], IA) 
        _, IA, _ = np.intersect1d(metadata['ch_names_mp'], lf_bad, return_indices = True )
        data['mp_channels'] = np.delete(data['mp_channels'], IA)
        metadata['ch_names_mp'] = np.delete(metadata['ch_names_mp']. IA)

        return data, metadata

'''
