#!/usr/bin/env python
# coding: utf-8

# # MITSL2IA evaluation experiments
# 
# This notebook and general evaluation pipeline was adapted from code written for and used in Chapter 3 of Aksënova (2020). All code in the first few sections was taken verbatim from https://github.com/alenaks/subregular-experiments. The section 'Experiment 10: Multi-tier Input-Sensitive Harmony' was taken from De Santo & Aksënova (2021), with code taken verbatim from https://github.com/alenaks/2IMTSL. The MITSL Experiments section was adapted from Aksënova (2020), by changing to use a MITSL implemented in local_sigmapie/code/mitsl_class.py, which is the main contribution for this work and was adapted from the rest of the code. The python classes in local_sigmapie are needed to run this notebook, as are the natural language corpora files in the natural_data folder.
# 
# # NEW! String Extension Learning Experiments
# 
# I adapted the languages contained in this notebook to be a test of the itsl string extension learning adaptations. Look for MITSL Experiment 1 for documentation in comments. Look below the MITSL experiments for further experiments. This notebook tests whether the adapted string extension learner can learn a variety of languages for k=2 (tier dependency window size) and m=2 (symbol width). See Lambert.py for more details

# # Generators and evaluators: the setup for the experiments
# 
# ## Step 1: loading dependencies, including _SigmaPie_

# In[1]:


import codecs
from random import choice, randint
from pprint import pprint

'''%cd local_sigmapie/code/
from main import *
%cd ../..'''
from Lambert import *

# In[2]:


def wrong(g, acc, sigstar):
    '''
    This tests a grammar against an acceptor on a list of strings, and returns every string where the grammar gives the 'wrong' answer
    '''
    return [w for w in sigstar if scan(g, w) != acc(w)]

# ## Step 2: defining general harmonic evaluator
# 
# Here some info on the artificial harmonic generator used here, originally from Chapters 3 and 4 of Aksënova (2020).
# It can generate two types of samples:
# 
# * Samples of **well-formed words**, i.e. words that don't violate the rules of the harmony; and
# * Samples of **underlying -> surface forms**, i.e. pairs where the first member has only the first value of every harmonic class specified (i.e. the feature that needs to be spread is given), and all consecutive members of the same class are masked as the name of that class.
# 
# ### Parameters of the generator
# 
# List of the parameters that are available:
# 
# * number of strings to be generated;
# * harmonic classes and their members (harmonic class is a class of segments that don't co-occur unless there is a blocker in-between them);
# * minimal and maximal cluster length of each of the harmonic classes;
# * blockers and the new domain that they introduce;
# * a probability of observing a blocker (1 / n, where n is a parameter): basically means "every n-th cluster will be the blocker".

# In[3]:


class Harmony(object):
    """
    Class defining the toy generator for the harmonic datasets.
    
    Attributes:
        cl_members (dict): dictionary of the type {(harmonic_class_1):class_id_1,
            (harmonic_class_2):class_id_2, ...} that contains info about the present
            harmonic classes. Note that the transparent element can be encoded by 
            a harmonic class containing a single element.
            Example: {("a", "o"):"A", ("b", "p"):"B", ("c"):"C"}
        cl_lengths (dict): dictionary of the type {class_id:(min_len, max_len)},
            where min_len and max_len denote the min and max len of the cluster
            made out of elements of class_id.
            Example: {"A":(1, 3), "B":(2, 4), "C":(4, 8)}
        blockers (dict): dictionary of the type {"b_1":"u_1", "b_2":"u_2", ...} where
            "b" is the blocker, and "u" is the newly introduced value.
            Example: {"t":"p"}
        blocker_prob (int): a chance of observing a blocker, the P evaluates from
            (1/blocker_prob).
            Example: 5
    """
    def __init__(self, cl_members, cl_lengths = None, blockers = None, blocker_prob = 5):
        """
        Init function for the Harmony class.
        """
        self.cl_members = cl_members
        if cl_lengths is not None:
            self.cl_lengths = cl_lengths
        else:
            self.cl_lengths = {i:(1, 3) for i in self.cl_members.values()}
        self.blockers = blockers
        self.blocker_prob = blocker_prob
        

        
    def generate_words(self, n = 3, length = 10):
        """
        Generates n strings of a given length.
        
        Arguments:
            n (int): how many strings need to be generated;
            length (int): length of the strings.
            
        Returns:
            list[str]: n generated strings.
        """
        # check if the harmony rules are well-formed
        if not self._verify_classes():
            raise("Cannot generate dataset: the sets are overlapping.")
            
        # unpack the dictionary for a quicker lookup
        unpacked = self._unpack_classes()
        transparent = self._transparent()
        generated = [self._generate(unpacked, length) for i in range(n)]
        return generated
    

    def generate_pairs(self, n = 3, length = 10):
        """
        Generates n pairs of strings of a given length.
        
        Arguments:
            n (int): how many strings need to be generated;
            length (int): length of the strings.
            
        Returns:
            list[tuple[str]]: n generated pairs of strings.
        """
        transparent = self._transparent()
        outputs = self.generate_words(n, length)
        inputs = self._mask_words(outputs, transparent)
        return list(zip(inputs, outputs))
        
        
    def _generate(self, unpacked, length):
        """
        Generates a set of strings; helper function.
        
        Output type: list[str]
        """
        
        # initialize the specifications of this particular string
        string = ""
        specs = self._specify()
        
        while len(string) < length:
            
            
            # check if we can now output the blocker
            if self.blockers is not None:
                while randint(1, self.blocker_prob) == 1:
                    b = choice(list(self.blockers))
                    string += b
                    
                    if len(string) == length:
                        return string
                    
                    # rewrite the specification because of the blocker
                    if self.blockers[b] not in specs:
                        for spec in specs:
                            if unpacked[spec] == unpacked[self.blockers[b]]:
                                specs.remove(spec)
                                specs.append(self.blockers[b])
                                break
                                
            # make sure that we don't generate cluster of the same
            # harminic set as the previous one
            if len(string) > 0:
                change = string[-1] in unpacked
            else:
                change = False
            
            # select and add new possible character as many times as
            # cl_lengths indicate
            if not change:
                newchar = choice(specs)
            else:
                collection = [i for i in specs]
                collection.remove(string[-1])
                newchar = choice(collection)
            freq_b, freq_e = self.cl_lengths[unpacked[newchar]]
            string += newchar * randint(freq_b, freq_e)
            
            # output
            if len(string) > length:
                string = ""
            elif len(string) == length:
                return string
            
            
    def _mask(self, string, transparent):
        """
        Masks all non-initial mentions of the specified allophone: helper function.
        
        Output type: str
        """
        classes = {i:False for i in self.cl_members.keys()}
        undergoers = self._undergoers()
        new = ""
        for s in string:
            if (s in undergoers) and (s not in transparent.values()):
                for c in classes:
                    
                    # rewrite the non-initial mention of the harmonic set member
                    # as its harmony_class_id
                    if s in c and not classes[c]:
                        classes[c] = True
                        new += s
                    elif s in c:
                        new += self.cl_members[c]
            else:
                new += s
        return new

    
    def _mask_words(self, words, transparent):
        """
        Masks every word of a given list; helper function.
        
        Output type: list[str]
        """
        return [self._mask(w, transparent) for w in words]
            
            
    def _undergoers(self):
        """
        Collects all undergoers; helper function.
        
        Output type: list[char]
        """
        items = []
        for i in self.cl_members:
            items.extend(list(i))
        return items
    
    def _transparent(self):
        """
        Checks if there are transparent items, i.e. if there is
        a harmonic class or classes that only contain a single item.
        
        Output type: dict[str:str]
        """
        transparent = dict()
        for i in self.cl_members:
            if len(i) == 1:
                transparent[self.cl_members[i]] = i[0]
        return transparent
        
        
    def _verify_classes(self):
        """
        Verifies that no set (harmonic sets or the set of blockers)
        overlaps with each other.
        
        Output type: bool
        """
        items = self._undergoers()
        if self.blockers is not None:
            block_ok = all([i not in items for i in self.blockers])
        else:
            block_ok = True
        return len(items) == len(set(items)) and block_ok
    
    
    def _unpack_classes(self):
        """
        Creates a dictionary where every harmonizing element 
        is mapped to its harmonic class; helps to optimize 
        the lookup of this information.
        
        Output type: dict
        """
        items = self._undergoers()
        unpacked = {}
        for i in items:
            for j in self.cl_members:
                if i in j:
                    unpacked[i] = self.cl_members[j]
        return unpacked

    
    def _specify(self):
        """
        Randomly initialize a specification from all given
        harmonic datasets.
        
        Output type: list[char]
        """
        return list(map(choice, self.cl_members.keys()))

# ### Examples of the data generated by AHG
# 
# #### Parallel vowel and consonant harmonies
# Harmony of a class "A" that contains "a" and "o" and of a class "B" that contains "b" and "p". Linguistically, these are simultaneous and independent vowel and consonant harmonies.

# In[4]:


s1 = {("a", "o"):"A", ("b", "p"):"B"}
h1 = Harmony(s1)

# Now, let's generate a sample of well-formed words.

# In[5]:


print(h1.generate_words(n = 5, length = 10))

# #### Harmony with a transparent element
# 
# Transparent, or irrelevant items that only introduce the long-distance effect in the dataset can be modeled by providing an extra harmonic class with just a single item in it.

# In[6]:


s2 = {("a", "o"):"A", ("x"):"X"}
l2 = {"A":(1, 2), "X":(2, 4)}
h2 = Harmony(s2, l2)

# Now, us generate some well-formed words.

# In[7]:


print(h2.generate_words(n = 5, length = 10))

# #### Parallel vowel and consonant harmonies with a blocking effect
# 
# Harmony of a class "A" and of a class "B", where if "t" occurred, "p" cannot be observed anymore: class "B" changes its specification to "p". Namely, "t" is a blocker that only allows for "p" after itself.
# 
# Additionally, clusters of the A-element consist usually from 1 to 3 elements, and clusters of the B-elements are 2 to 4 elements long. The probability of observing the blocker is $\frac{1}{4}$ at every step of the generation.

# In[8]:


s3 = {("a", "o"):"A", ("b", "p"):"B"}
l3 = {"A":(1, 3), "B":(2, 4)}
b3 = {"t":"p"}
p3 = 4
h3 = Harmony(s3, l3, b3, p3)

# Let's first generate some well-formed words.

# In[9]:


print(h3.generate_words(n = 5, length = 10))

# ## Step 3: Turkish generators and evaluators
# 
# The following two functions are used to verify the well-formedness of generated Turkish or fake Turkish words:
#   * `backness_harmony` takes a string as input and tells if that strings is well-formed with respect to the rules of Turkish backness harmony;
#   * `rounding_harmony` does the same thing for the rounding harmony.

# In[10]:


def backness_harmony(string):
    """
    Tells if a string is well-formed according to rules
    of Turkish backness harmony.
    """
    front_class, back_class = "Iaou", "ieOU"
    front, back = False, False
    
    for v in front_class + back_class:
        if v in string:
            front = True if v in front_class else front
            back = True if v in back_class else back

    return not (front and back)

# In[11]:


def rounding_harmony(string):
    """
    Tells if a string is well-formed according to rules
    of Turkish rounding harmony.
    """
    high, low, rounded = "iIuU", "aeoO", "uUoO"
    
    vowels = "".join([v for v in string if v in high + low])
    if len(vowels) < 2:
        return True
    
    ro = vowels[0] in rounded
    
    for v in vowels[1:]:
        if v in low:
            if v in rounded:
                return False
            ro = False
        elif (ro and v not in rounded) or (not ro and v in rounded):
            return False
            
    return True

# In[12]:


def backness_and_rounding(string):
    return backness_harmony(string) and rounding_harmony(string)

# Additionally, to generate simplified Turkish data, `turkish_word` and `generate_turkish_words` will generate a single word and a dataset, correspondingly.
# 
# Their parameters are:
# * `length` is a desired length of the Turkish word;
# * `cond` is a choice of "consonant" that will be separating the vowels;
# * `vowel_cluster` is a tuple of integers representing minimal and maximal length of the vowel cluster;
# * `cons_cluster` is a tuple of integers representing minimal and maximal length of the consonantal cluster;
# * `n` (available for `generate_turkish` only) is the number of the examples that need to be generated.

# In[13]:


def turkish_word(length = 10, cons = "x", vowel_cluster = (1, 2),
                          cons_cluster = (0, 3)):
    """
    This generator generates fake Turkish words: namely, the words in which
    the harmonic system and rules of Turkish are preserved, but all consonants
    were substituted by a single given consonant.
    
    Arguments:
    * length (int): a length of a word that needs to be generated;
    * cons (str): a single character (or an empty string if only vowels
                  need to be generated), a "choice" of the consonant 
                  that makes this harmony long-distant;
    * vowel_cluster (tuple[int, int]): a tuple of integers representing
                                       minimal and maximal length of
                                       the vowel cluster;
    * cons_cluster (tuple[int, int]): a tuple of integers representing
                                      minimal and maximal length of
                                      the consonantal cluster.
                                      
    Returns:
    * str: a fake Turkish harmonic word, where all consonants are masked.
    """
    if length < 1:
        raise ValueError("Words cannot be so short.")
    
    vowels = {
        (True, True, True):"u",
        (True, True, False):"I",
        (True, False, True):"o",
        (True, False, False):"a",
        (False, True, True):"U",
        (False, True, False):"i",
        (False, False, True):"O",
        (False, False, False):"e"
    }
    
    backness = choice([True, False])
    height = choice([True, False])
    rounding = choice([True, False])
    
    specs = (backness, height, rounding)
    word = ""
    
    if choice([0, 1]):
            word += "x" * randint(*cons_cluster)
            
    while len(word) < length:
        vc = vowels[specs] * randint(*vowel_cluster)
        
        # this part is neededd to avoid the word-initial *oo clusters
        if len(vc) > 1 and not height and rounding:
            rounding = False
            vc = vc[0] + vowels[(backness, height, rounding)] * (len(vc) - 1)
            
        word += vc
        word += "x" * randint(*cons_cluster)
        
        height = choice([True, False])
        rounding = False if not height else rounding
        specs = (backness, height, rounding)
        
    return word[:length]

# In[14]:


def generate_turkish_words(n = 10, length = 10, cons = "x",
                           vowel_cluster = (1, 2), cons_cluster = (1, 3)):
    """
    This generator generates a list of fake Turkish words.
    
    Arguments:
    * n (int): a number of strings that need to be generated;
    ... for the rest of the arguments, see generate_turkish_word.
    
    Outputs:
    * list: the list containing n fake Turkish words.
    """
    return [turkish_word(length, cons, vowel_cluster, cons_cluster) for i in range(n)]

# ## Step 4: other harmonic evaluators
# 
# The function `harmonic_evaluator` below takes two arguments: `data` and `rule`. `data` is a list of words that need to be evaluated, and `rule` is the evaluation function for some concrete harmony. This function will be further used in order to evaluate the performance of the learners on the generated datasets.

# In[15]:




def harmonic_evaluator(data, rule):
    """
    Evaluates the provided data with respect to a given
    rule of harmony.
    
    Arguments:
    * data (list[str]): a list of strings tht need to be evaluated;
    * rule (function): a function that evaluates a string according
                       to some harmony.
                       
    Results:
    * Prints the report that shows if the data follows the rule.
    """
    correct = 0
    incorrect = set()
    #for w in progressBar(data, prefix = "evaluating"):# #
    for w in data:# #
        #correct = (correct + 1) if rule(w) else correct
        if rule(w):
            correct += 1
        else:
            incorrect.add(w)
        
    ratio = (correct / len(data))
    '''print(f"Percentage of harmonic words: {int(ratio * 100)}%.")
    print(incorrect)
    return incorrect''' # # #
    return ratio # # #

# ### Finnish
# 
# Finally, `front_harmony` defines a function that tells if a given string follows a rule of Finnish vowel harmony.

# In[16]:


def front_harmony(string):
    """
    Tells if a string is well-formed according to rules
    of Finnish backness harmony.
    """
    front_class, back_class = "AOy", "aou"
    front, back = False, False
    
    for v in front_class + back_class:
        if v in string:
            front = True if v in front_class else front
            back = True if v in back_class else back

    return not (front and back)

# ### Fake harmony evaluators

# In[17]:


def single_harmony_no_blockers(string):
    """
    Checks if a single [a, o] harmony is well-formed.
    """
    return not("a" in string and "o" in string)

# In[18]:


def single_harmony_with_blockers(string):
    """
    Checks if a single [a, o] harmony with a blocker f:a is well-formed.
    """
    if "f" in string:
        s1 = string[:string.index("f")]
        s2 = string[string.index("f") + 1:]
        return single_harmony_no_blockers(s1) and (not "o" in s2)
    else:
        return single_harmony_no_blockers(string)

# In[19]:


def double_harmony(string, group = ["a", "o", "u", "e"]):
    """
    Tells if a string contains only one out of four
    (vowel) classes; check that at most one class
    of vowels occurs within one word.
    
    Arguments:
    * string (str): a string that needs to be verified;
    * group (list[char]): the harmonic class.
    """
    assert len(group) == 4
    classes = 0
    
    for i in group:
        classes = (classes + 1) if i in string else classes
        
    return classes in [0, 1]

# In[20]:


def double_harmony_no_blockers(string):
    """
    Checks if a double [a, o] and [b, p] harmony is well-formed.
    """
    vowels = not("a" in string and "o" in string)
    consonants = not("b" in string and "p" in string)
    return vowels and consonants

# In[21]:


def double_harmony_with_blockers(string):
    """
    Checks if a double [a, o] and [b, p] harmony with a blocker t:p
    is well-formed.
    """
    if "a" in string and "o" in string:
        return False
    
    if "t" in string:
        s1 = string[:string.index("t")]
        s2 = string[string.index("t") + 1:]
        return double_harmony_no_blockers(s1) and ("b" not in s2)
    else:
        return double_harmony_no_blockers(string)

# ## Step 5: Word-final devoicing generators and evaluators
# 
# The functions `word_final_devoicing` and `generate_wfd` imitate the process of word-final devoicing.
# The former one generates a string or a pair of strings (UR -> SF) implementing that rule, and the latter one generates dataset consisting of ones.
# 
# Their arguments are the following:
# * `sigma` is a list of symbols that can be used in the words;
# * `devoice` contains two tuples, where the first tuple represents voiced obstruents, and the second one stands for their voiceless counterparts;
# * `length` is the length of the intended words;
# * if `pairs` is True, (UG, SF) pairs will be returned, if False, only the surface forms;
# * `n` (available only for `generate_wfd`) is a number of strings or pairs that need to be generated.

# In[22]:


def word_final_devoicing(sigma = ("a", "b", "p"), devoice = (("b"), ("p")),
                         length = 10, pairs = False):
    """
    This function generates either a word grammatical with respect to a rule
    of the word final devoicing, or a fake UG -> SF pair.
    
    Arguments: 
    * sigma (list[str]): a list of symbols that can be used in the words;
    * devoice (tuple[tuple, tuple]): the first tuple represents voiced
                                     obstruents, and the second one stands
                                     for their voiceless counterparts;
    * length (int): a length of the intended words;
    * pairs (bool): if True, (UG, SF) pairs will be returned, if False, only
                    the surface forms.
                    
    Outputs:
    * str/tuple: a string or a tuple of strings (depending on the parameter 
                 `pairs`) representing the application of the word-final 
                 devoicing.
    """
    if length < 1:
        raise ValueError("The string has a very weird length.")
        
    before, after = devoice
    string = "".join([choice(sigma) for i in range(length)])
    
    if string[-1] not in before:
        return (string, string) if pairs else string
    
    devoiced = string[:-1] + after[before.index(string[-1])]
    return (string, devoiced) if pairs else devoiced

# In[23]:


def generate_wfd(n = 10, sigma = ("a", "b", "p"), devoice = (("b"), ("p")),
                 length = 10, pairs = False):
    """
    Generates a set of strings or pairs that satisfy the rule of
    the word-final devoicing.
    
    Arguments:
    * n (int): the number of strings that need to be generated;
    ... for the rest of the arguments see word_final_devoicing.
    
    Outputs:
    * list: a list of strings or tuples (depending on the parameter `pairs`)
            representing the application of the word-final devoicing.
    """
    return [word_final_devoicing(sigma, devoice, length, pairs) for i in range(n)]

# The following function `evaluate_wfd_words` evaluates words with respect to the rules of the word-final devoicing.

# In[24]:


def evaluate_wfd_words(data, voiced = ("b")):
    """
    Evaluates the provided words with respect to the rule 
    of the word-final devoicing.
    
    Arguments:
    * data (list[str]): a list of strings tht need to be evaluated;
    * voiced (tuple[char]): a list of voiced characters, i.e. those
                            that cannot be word-final.
                       
    Results:
    * Prints the report that shows if the data follows the ule.
    """
    correct = 0
    #for w in progressBar(data, prefix = "evaluating"):# #
    for w in data:# #
        
        if not len(w):
            correct += 1
            continue
            
        correct = (correct + 1) if w[-1] not in voiced else correct
        
    ratio = (correct / len(data))
    # # # print(f"Percentage of well-formed words: {int(ratio * 100)}%.")
    return ratio

# As before, we can generate some words or pairs of words representing the rule of the word-final devoicing, and then check if the evaluator considers that those datasets are well-formed.

# In[25]:


evaluate_wfd_words(generate_wfd(n = 1000, pairs = False))

# ## Step 6: UTP generator and evalurator
# 
# The function `generate_tonal_pattern` takes a length of the string that needs to be generated, and returns a random string of raising (H) and falling (L) tones as output. `utp_tones` takes that string of tones as input, and rewrites it according to the UTP rules: no L tones are allowed in-between two H tones.

# In[26]:


def generate_tonal_pattern(length = 5):
    """ Generates a random sequence of tones of a given length. """
    return "".join(choice(["H", "L"]) for i in range(length))

# In[27]:


def utp_tones(string):
    """ Rewrites a tonal string with respect to the rules of UTP. """
    
    if set(string) not in [{"H", "L"}, {"H"}, {"L"}, set("")]:
        print(string)
        raise ValueError("Unexpected symbols in the tonal string!")
    if not ("H" in string and "L" in string):
        return string
    
    first_h = string.find("H")
    last_h = len(string) - string[::-1].find("H")
    return string[:first_h] + "H" * (last_h - first_h) + string[last_h:]

# Then, `generate_utp_strings` generates strings of tones that are well-formed accroding to the rules of UTP. As before, `n` signifies the number of strings that need to be generated, and `length` is the length of those strings.

# In[28]:


def generate_utp_strings(n = 10, length = 5):
    """ Generates n strings of tones that follow UTP rules. """
    return [utp_tones(generate_tonal_pattern(length)) for i in range(n)]

# Finally, `evaluate_utp_strings` and `evaluate_utp_pairs` calculate what is the percentage of the input data (strings or pairs of strings) is well-formed with respect to the rules of UTP.

# In[29]:


def evaluate_utp_strings(data):
    """ Evaluates the correctness of if the given sample of tonal strings. """
    correct = 0
    #for w in progressBar(data, prefix = "evaluating"):# #
    for w in data:# #
        correct = (correct + 1) if utp_tones(w) == w else correct
        
    ratio = (correct / len(data))
    # # # print(f"Percentage of well-formed tonal layers: {int(ratio * 100)}%.")
    return ratio

# As before, we can verify the correctness of the generator using the evaluation functions.

# In[30]:


evaluate_utp_strings(generate_utp_strings(n = 1000))

# ## Step 7: First-last harmony generators and evaluators

# In[31]:


def first_last_UR(n = 10, length = 10):
    """ Generates URs of first-last harmony words. """
    strings = []
    for i in range(n):
        new = choice(["a", "o"])
        new += "".join([choice(["a", "o", "x"]) for j in range(length - 2)])
        new += choice(["a", "o"])
        strings.append(new)
    return strings

def first_last(string):
    """ Makes the first and the last segment of the string the same. """
    return string[:-1] + string[0]

def first_last_words(n = 10, length = 10):
    """ Generates N first-last words. """
    return [first_last(w) for w in first_last_UR(n, length)]

# In[32]:


def evaluate_first_last_words(data):
    """
    Evaluates the correctness of if the given sample
    of first-last harmony (UR -> SF).
    """
    newdata = [i for i in data if len(i) > 1]
    if len(newdata) == 0 : return 1 # # #words with fewer than 2 characters pass by definition
    correct = 0
    #for w in progressBar(newdata, prefix = "evaluating"):# #
    for w in newdata:# #
        if w[0] == w[-1]:
            correct += 1
        
    ratio = (correct / len(newdata))
    # # #print(f"Percentage of first-last harmonic words: {int(ratio * 100)}%.")
    return ratio # # #

# In[ ]:




# ### Auxiliary functions

# In[33]:


def generate_sp_empty_word(alphabet, length = 5):
    return "".join([choice(alphabet) for i in range(length)])

def generate_sp_empty(alphabet, n = 10, length = 5):
    return [generate_sp_empty_word(alphabet, length) for i in range(n)]

# # Preparing training samples for the experiments
# 
# ### Experiment 1: Word-final devoicing
# 
# #### Artificial grammar: `toy_wfd`

# In[34]:


toy_wfd = generate_wfd(n = 1000)
print(toy_wfd[:15])

# #### Raw German data: `german_wfd`
# 
# In German, orthography doesn't reflect the word-final devoicing. So first of all, all word-final /b/, /d/ and /g/ are rewritten as /p/, /t/ and /k/, correspondingly. Additionally, words with "non-German" characters are removed. The data comes from the [wordlist by enz](https://github.com/enz/german-wordlist).

# In[35]:


german_data = []
with codecs.open('natural_data/german.txt', encoding='utf-8') as f:
    for line in f:
        if line != "":
            german_data.append(line[:-1])
            
print(len(german_data))
print(german_data[:10], "...")

# In[36]:


count_final_b = 0
count_final_d = 0
count_final_g = 0

for i in german_data:
    if i[-1] == "b":
        count_final_b += 1
    elif i[-1] == "d":
        count_final_d += 1
    elif i[-1] == "g":
        count_final_g += 1
        
print("Number of final /b/:", count_final_b) # 1599, or 0.2% words
print("Number of final /d/:", count_final_d) # 15294, or 2.2% words
print("Number of final /g/:", count_final_g) # 17098, or 2.4 % words

# In[37]:


ban = ['à', 'á', 'â', 'å', 'ç', 'è', 'é', 'ê', 'ë', 'í', 'î', 'ñ', 'ó', 'õ', 'ú',
       'û', 'č', 'ē', 'ī', 'ł', 'ō', 'œ', 'š', 'ū']

german_wfd = []
banned_words = []

for w in german_data:
    
    word = w.lower()
    
    illegal = False
    for b in ban:
        if b in word:
            banned_words.append(word)
            illegal = True
            break
            
    if illegal:
        continue
        
    if word[-1] == "b":
        word = word[:-1] + "p"
    elif word[-1] == "d":
        word = word[:-1] + "t"
    elif word[-1] == "g":
        word = word[:-1] + "k"
        
    german_wfd.append(word)

print(len(german_wfd))
print("Clean dataset:", german_wfd[:15], "...\n")

print(len(banned_words))
print("Banned words:", banned_words[:10], "...")

# #### Masked German data: `german_wfd_masked`
# 
# Now, let us substitute all segments that are not /p/, /t/, /k/, /b/, /d/, /g/ by "a".
# It will help further to try the learning algorithms on data that has less local dependencies.

# In[38]:


german_wfd_masked = []
for w in german_wfd:
    new = ""
    for s in w:
        if s in ["p", "t", "k", "b", "d", "g"]:
            new += s
        else:
            new += "a"
    german_wfd_masked.append(new)
german_data.append("")
    
print(len(german_wfd_masked))
print("Masked words:", german_wfd_masked[10:15], "...")

# ### Experiment 2: One vowel harmony, no blockers
# 
# #### Artificial grammar: `toy_vhnb`

# In[39]:


ts2 = {("a", "o"):"A", ("x"):"X"}
tl2 = {"A":(1, 2), "X":(2, 4)}
th2 = Harmony(ts2, tl2)
toy_vhnb = th2.generate_words(n = 1000)
print(toy_vhnb[:15], "...")

# #### Raw Finnish data: `finnish_harmony`
# 
# The next step is to have a dataset from a natural language that implements a single harmony.
# Here, we use Finnish data from [this link](https://github.com/douglasbuzatto/WordLists/blob/master/finnish-words.txt).

# In[40]:


finnish_data = []
with codecs.open('natural_data/finnish.txt', encoding='utf-8') as f:
    for line in f:
        if line != "":
            finnish_data.append(line[:-2])
            
print(len(finnish_data))
print(finnish_data[:10], "...")

# Then the unharmonic stems are filtered to clean the data. Apart from the digits and punctuations, words are also filtered that contain `}` that stands here in this dataset for Swedish `å`, and therefore is ill-defined in terms of the harmony. Then I rewrite `{` as `ä` and `|` as `ö` in order to normalize the spelling with respect to Turkish examples further. Finally, non-harmonic stems are filtered.

# In[41]:


ban = [' ', '*', '-', '.', '/', '0', '1', '2', '3', '4', '6', '8', '9', ':', '}']

finnish_harmony = []
banned_words = []
non_harmonic = []

for w in finnish_data:
    
    word = w.lower()
    
    illegal = False
    for b in ban:
        if b in word:
            banned_words.append(word)
            illegal = True
            break
            
    if illegal:
        continue
    
    word = word.replace("{", "A")
    word = word.replace("|", "O")
    if front_harmony(word):
        finnish_harmony.append(word)
    else:
        non_harmonic.append(word)

print(len(finnish_harmony))
print("Clean dataset:", finnish_harmony[105000:105015], "...\n")

print(len(banned_words))
print("Banned words:", banned_words[10:15], "...\n")

print(len(non_harmonic))
print("Non-harmonic words:", non_harmonic[:3], "...")

# #### Masked Finnish data: `finnish_harmony_masked`
# 
# Finally, all the transparent Finnish elements are masked in the dataset.

# In[42]:


finnish_harmony_masked = []
for w in finnish_harmony:
    new = ""
    for s in w:
        if s in ["A", "O", "y", "a", "o", "u"]:
            new += s
        else:
            new += "x"
    finnish_harmony_masked.append(new)
    
print(len(finnish_harmony_masked))
print("Masked words:", finnish_harmony_masked[170005:170010], "...")

# ### Experiment 3: One vowel harmony with blockers
# 
# #### Artificial grammar: `toy_vhwb`

# In[43]:


harmonic_classes = {("a", "o"):"A", ("x"):"X"}
blockers = {"f":"a"}
cluster_lengths = {"A":(1, 2), "X":(1, 3)}
blocker_prob = 5
h = Harmony(harmonic_classes, cluster_lengths, blockers, blocker_prob)
toy_vhwb = h.generate_words(n = 1000)
print(toy_vhwb[:15], "...")

# ### Experiment 4: Two vowel harmonies, no blockers
# 
# #### Artificial grammar: `toy_shnb`

# In[44]:


is2 = {("a", "e", "o", "u"):"A", ("x"):"X"}
il2 = {"A":(1, 2), "X":(2, 4)}
ih2 = Harmony(is2, il2)
toy_shnb = ih2.generate_words(n = 1000)
print(toy_shnb[:15], "...")

# ### Experiment 5: Two vowel harmonies with vowel blockers
# 
# #### Artificial grammar: `toy_mhwb`

# In[45]:


toy_mhwb = generate_turkish_words(n = 5000, length = 8, cons_cluster = (0, 3))
toy_mhwb.extend(generate_turkish_words(n = 5000, length = 6, cons_cluster = (0, 3)))# # #Changed 3 to 4 on all cons_cluster parameters
toy_mhwb.extend(generate_turkish_words(n = 5000, length = 4, cons_cluster = (0, 3)))
print(toy_mhwb[:15], "...")

# #### Raw Turkish data: `turkish_harmony`
# 
# The following is a dataset of Turkish harmony from [here](http://www.swarthmore.edu/SocSci/harmony/public_html/dummyresults.html). Non-native Turkish words are removed, and also the ones that do not follow the rules of backness and rounding harmony.

# In[46]:


banned = []
non_harmonic = []
turkish_harmony = []

with codecs.open('natural_data/turkish.txt', encoding='utf-8') as f:
    
    ban = ["!", "-", "w", "x", "A"]
    for line in f:
        if line == "":
            continue
        w = line[:-2]
        
        if any([(i in w) for i in ban]):
            banned.append(w)
            continue
            
        if backness_harmony(w) and rounding_harmony(w):
            w = w.replace("K", "k")
            turkish_harmony.append(w)
        else:
            non_harmonic.append(w)
            
print(len(banned))
print(banned[:30], "...\n")

print(len(non_harmonic))
print(non_harmonic[:30], "...\n")
            
print(len(turkish_harmony))
print(turkish_harmony[:30], "...")

# #### Masked Turkish data: `turkish_harmony_masked`
# Then, the Turkish harmonic data is simplified by masking all non-vowels as `x`.

# In[47]:


turkish_harmony_masked = []
for w in turkish_harmony:
    new = ""
    for s in w:
        if s in "iIuUaeoO":
            new += s
        else:
            new += "x"
    turkish_harmony_masked.append(new)
    
print(len(turkish_harmony_masked))
print("Masked words:", turkish_harmony_masked[12005:12010], "...")

# ### Experiment 6: Vowel harmony and consonant harmony, no blockers
# 
# #### Artificial grammar: `toy_dhnb`

# In[48]:


iss = {("a", "o"):"A", ("b", "p"):"B"}
ihs = Harmony(iss)
toy_dhnb = ihs.generate_words(n = 1000)
print(toy_dhnb[:15], "...")

# ### Experiment 7: Vowel harmony and consonant harmony with blockers
# 
# #### Artificial grammar: `toy_dhwb`

# In[49]:


aa = {("a", "o"):"A", ("b", "p"):"B"}
bb = {"A":(1, 2), "B":(1, 2)}
cc = {"t":"p"}
dd = 5
hmm = Harmony(aa, bb, cc, dd)
toy_dhwb = hmm.generate_words(n = 5000)
print(toy_dhwb[:15], "...")

# ### Experiment 8: Tonal plateauing
# #### Artificial grammar: `toy_utp`

# In[50]:


toy_utp = generate_utp_strings(n = 1000)
print(toy_utp[:15], "...")

# ### Experiment 9: First-last harmony
# #### Artificial grammar: `first_last_data`

# In[51]:


first_last_data = first_last_words(n = 5000)
print(first_last_data[:15], "...")

# # Experiment 10: Multi-tier Input-Sensitive Harmony
# 
# The trigger for a long-distance assimilation depends on a local context. For example, `e` immediately before `x` prohibits `a` anywhere further after `e` in the string. Then `eaaxaae` and `axaexeeexx` are good, while `exxae` is not.

# #### 1. Preparing a class to encode input sensitive rules

# In[52]:


class SSRule(object):
    """ A generic template for a input-sensititve rule. 
    
    * symbols (tuple): list of tier symbols relevant for the generalization;
    * target (str): a target character context of which is important;
    * right_context (str): a context in which a target character
                           is projected on the tier;
    * can_follow (tuple): a list of tier symbols that are allowed after
                         the target character is projected.
    """
    def __init__(self, symbols, target, right_context, can_follow):
        self.symbols = symbols
        self.target = target
        self.right_context = right_context
        self.can_follow = can_follow

    def is_grammatical(self, string):
        """ Checks if the given form follows a rule that is encoded.
        
        * string (str): a string well-formedness of which needs to be checked.
        """
        
        # get rid of all irrelevant symbols (not symbols and contexts)
        string = "".join([i for i in string if i in list(self.symbols) + [self.right_context]])
        
        # construct a tier of that strings
        tier = ""
        for i in range(len(string)):
            if string[i] in self.symbols:
                if string[i] == self.target and i < len(string) - 1 and\
                    string[i + 1] == self.right_context:
                    tier += self.target
                elif string[i] != self.target:
                    tier += string[i]

        # check if that tier is well-formed
        for t in range(len(tier)):
            if tier[t] == self.target and t < len(tier) - 1 and\
                tier[t + 1] not in self.can_follow:
                return False
        return True

# #### 2. Writing a generator of a sequence grammatical wrt the rule

# In[53]:


def generate_rule_sequence(rule, length = 7, grammatical = True):
    """ This function generates a sequence of symbols (un)grammatical 
        with respect to the given rule.
        
    * rule (SSRule): a rule describing an input sensitive dependency;
    * length (int): length of the generated sequence;
    * grammatical (bool): produces correct form when set to True, and 
                          makes a mistake when set to False.
    """
    
    # the generation of the well-formed sequence is done by a simplistic FSA
    sequence = ""
    state = 0
    for i in range(length):
        
        # State 0: the target was not observed
        if state == 0:
            sequence += choice(list(rule.symbols) + [rule.right_context])
            if sequence[-1] == rule.target:
                state = 1
                
        # State 1: the target was observed
        elif state == 1:
            sequence += choice(list(rule.symbols) + [rule.right_context])
            if sequence[-1] == rule.right_context:
                state = 2
            elif sequence[-1] != rule.target:
                state = 0
                
        # State 2: the right context was observed
        elif state == 2:
            sequence += choice(list(rule.can_follow) + [rule.right_context])
                
    # if the ungrammatical form is needed, a violating sequence is generated
    # and inserted into a random position within the sequence
    if not grammatical:
        violate = rule.target + rule.right_context +\
            choice([i for i in list(rule.symbols) if i not in rule.can_follow])
        index_violate = choice(range(length - 3))
        sequence = sequence[:index_violate] + violate + sequence[index_violate + 3:]
        
    return sequence

# #### 3. Intertwine

# In[54]:


def intertwine(str1, str2, r = (0, 3)):
    """ Intertwines two strings: str1 and str2. At every step, it takes
    some characters from one string, and then some characters from another.
    oxxooxa
    * str1 (str): the first string;
    * str2 (str): the second string;
    * r (tuple[int, int]): min and max+1 symbols to be taken.
    """
    new_string = ""
    current = choice([1, 2])
    while str1 or str2:
        if current == 1:
            cut = choice(range(r[0], r[1]))
            if len(str1) < cut:
                new = str1[:]
            else:
                new = str1[:cut]
            new_string += new
            str1 = str1[len(new):]
            current = 2
        elif current == 2:
            cut = choice(range(r[0], r[1]))
            if len(str2) < cut:
                new = str2[:]
            else:
                new = str2[:cut]
            new_string += new
            str2 = str2[len(new):]
            current = 1
    return new_string

# #### 4. Generator for the ITSL harmony
# A single locally-driven long-distance assimilation.

# In[55]:


def itsl_harmony_generate(n = 10, length = 10, grammatical = True,
                       rule_1 = None):
    """ Generates a collection words following the given rules of 
    input-sensitive dependencies that involve a single tier.
    
    * n (int): number of strings that need to be generated;
    * length (int): length of every one of the generated strings;
    * grammatical (bool): if set to True, the correctly harmonizing
                          forms are generated, and if set to False,
                          the disharmonic forms are produced;
    * rule_1 (SSRule): the first rule describing a long-distant input-
                      sensitive dependency.
    """
    
    # set the first rule
    if rule_1 == None:
        rule_1 = SSRule(symbols = ("o", "e", "a"), target = "o",\
                        right_context = "x", can_follow = ("a", "o"))
    strings = []
    for i in range(n):
        string = generate_rule_sequence(rule_1, length)
        if not grammatical:
            string = generate_rule_sequence(rule_1, length, grammatical = False)
        strings.append(string)
    return strings

# #### 5. Generator for the MITSL harmony
# Two locally-driven long-distance assimilations.

# In[56]:


def mitsl_harmony_generate(n = 10, length = 10, grammatical = True,
                       rule_1 = None, rule_2 = None):
    """ Generates a collection words following the given rules of the 
    input sensitive dependencies that involve several tiers.
    
    * n (int): number of strings that need to be generated;
    * length (int): length of every one of the generated strings;
    * grammatical (bool): if set to True, the correctly harmonizing
                          forms are generated, and if set to False,
                          the disharmonic forms are produced;
    * rule_1 (SSRule): the first rule describing a long-distant input-
                      sensitive dependency;
    * rule_2 (SSRule): the second rule describing a long-distant input-
                      sensitive dependency.
    """
    
    # set both rules
    if rule_1 == None:
        rule_1 = SSRule(symbols = ("o", "e", "a"), target = "o",\
                        right_context = "x", can_follow = ("a", "o"))
    if rule_2 == None:
        rule_2 = SSRule(symbols = ("b", "p", "d"), target = "b",\
                        right_context = "y", can_follow = ("b", "p"))
    
    strings = []
    for i in range(n):
        # generate two tiers independently, and then intertwine them
        # WARNING: the tier alphabets of the two rules cannot overlap
        #          (required by both learner and generator)
        len_part_1 = length // 2
        len_part_2 = length - len_part_1

        part_1 = generate_rule_sequence(rule_1, len_part_1)
        part_2 = generate_rule_sequence(rule_2, len_part_2)

        if not grammatical:
            mistake = choice(["R1", "R2", "both"])
            if mistake == "R1":
                part_1 = generate_rule_sequence(rule_1, len_part_1, grammatical = False)
            elif mistake == "R2":
                part_2 = generate_rule_sequence(rule_2, len_part_2, grammatical = False)
            else:
                part_1 = generate_rule_sequence(rule_1, len_part_1, grammatical = False)
                part_2 = generate_rule_sequence(rule_2, len_part_2, grammatical = False)

        # intertwining the two generated sequences
        new_string = intertwine(part_1, part_2)
        strings.append(new_string)
        
    return strings

# ### Tools: collecting data generators for the experiments

# In[57]:


def generate_harmony(kind="first-last", length=range(2, 7), number=1000):
    """
    Generates a harmony based on 3 parameters.
    
    Arguments:
    * kind (str): type of the harmony, choices:
        "first-last", "double", "assimilation-one", "assimilation-two"
    * length (range): a range of lengths of the intended strings
    * number (int): a number of strings to be generated
    
    Outputs:
    * list: a collection of strings.
    """
    
    # preparing data for easy generation
    lennum = {r:number // len(length) for r in length}
    hmap = {"assimilation-two" : mitsl_harmony_generate}
    
    # generating the data
    data = [i for l in lennum for i in hmap[kind](lennum[l], l)]
    
    # annotate the data with start- and end-markers >> and <<
    # # #return list(map(lambda string : ">>" + string + "<<", data)) # # #Annotation is not needed, SigmaPie-style learners do this on their own
    return list(map(lambda string : string, data))

# ### Create Evaluator

# In[58]:


def evaluate_mitsl_word(rules: list[SSRule], string: str):
    for rule in rules:
        if rule.target + rule.right_context not in string:
            continue
        '''chars = set()
        chars.update(rule.symbols)
        chars.update(rule.target)
        chars.update(rule.right_context)
        chars.update(rule.can_follow)
        tier = re.sub(f'[^{"".join(chars)}]', '', string)#replace all irrelevant characters'''
        tier = re.sub(f'[^{"".join(rule.symbols)}]', '', re.sub(f'.*?{rule.target + rule.right_context}', '', string))
        if any(s not in rule.can_follow for s in tier):
            return False
    return True

def evaluate_mitsl_words(strings):
    rule_1 = SSRule(symbols = ("o", "e", "a"), target = "o",\
                        right_context = "x", can_follow = ("a", "o"))
    rule_2 = SSRule(symbols = ("b", "p", "d"), target = "b",\
                        right_context = "y", can_follow = ("b", "p"))
    
    correct = 0
    incorrect = set()
    for string in strings:
        if evaluate_mitsl_word([rule_1, rule_2], string):
            correct += 1
        else:
            incorrect.add(string)
    ratio = (correct / len(strings))
    '''print(f"Percentage of harmonic words: {int(ratio * 100)}%.")
    print(incorrect)''' # # #
    return ratio

# ### Create Dataset

# In[59]:


assim_two = generate_harmony("assimilation-two", range(2, 8), number = 10000)

# ### Quick reference to the datasets
# 
# * **Word-final devoicing**
#   * `toy_wfd` (1,000 words)
#   * `german_wfd` (685,147 words)
#   * `german_wfd_masked` (131,938 words)
#   
#   
# * **Single vowel harmony, no blockers**
#   * `toy_vhnb` (1,000 words)
#   * `finnish_harmony` (250,805 words)
#   * `finnish_harmony_masked` (77,108 words)
#   
#   
# * **Single vowel harmony with blockers**
#   * `toy_vhwb` (1,000 words)
#   
#     
# * **Two vowel harmonies, no blockers**
#   * `toy_shnb` (1,000 words)
#   
#   
# * **Two vowel harmonies with vowel blockers**
#   * `toy_mhwb` (15,000 words)
#   * `turkish_harmony` (14,434 words)
#   * `turkish_harmony_masked` (1,769 words)
#   
#   
# * **Vowel harmony and consonant harmony, no blockers**
#   * `toy_dhnb` (1,000 words)
#   
#   
# * **Vowel harmony and consonant harmony with blockers**
#   * `toy_dhwb` (1,000 words)
#   
#   
# * **Unbounded tonal plateauing**
#   * `toy_utp` (1,000 words)
#   
#   
# * **First-last harmony**
#   * `first_last_data` (5,000 words)  
#   
# 
# * **First-last harmony**
#   * `assim_two` (10,000 words)

# In[60]:


import pickle, os

def save(i, sample, acc, sigstar, g, wrong):
    '''
    This is a simple helper method to pickle a bunch of experiment outputs in case the jupyter kernel crashes
    '''
    os.system(f'rm -rf {i}'); os.system(f'mkdir {i}')
    pickle.dump(sample, open(f'{i}/{"sample"}', 'wb'))
    pickle.dump(list(sigstar), open(f'{i}/{"sigstar"}', 'wb'))
    pickle.dump(g, open(f'{i}/{"g"}', 'wb'))
    pickle.dump(list(wrong), open(f'{i}/{"wrong"}', 'wb'))

# # MITSL experiments
# 
# ## Experiment 1: Word-final devoicing

# ### Artificial grammar

# In[61]:


'''this = "mitsl1"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_wfd
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
evaluate_wfd_words(globals()[this+"_sample"])
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''

acc1 = lambda w : evaluate_wfd_words([w])           #create an acceptor function which the grammar should learn to mimic, using the above acceptors from Aksënova (2020)
sigstar1 = list(star(set(''.join(toy_wfd)), 5))     #generate all strings made from this language's alphabet up to length 5

g1 = learn(toy_wfd + [""], k=2,m=2)                 #learn a k=2,m=2 grammar from this sample

wrong1 = wrong(g1, acc1, sigstar1)                  #find all strings in sigma* where this grammar gives the wrong answer 

save(1, toy_wfd, acc1, sigstar1, g1, wrong1)        #save the results to be used later (see the section after experiment 16)


# ### German simplified word-final devoicing

# In[62]:


"""'''this = "mitsl2"
globals()[this] = MITSL(polar = "n")
globals()[this].data = german_wfd_masked
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
evaluate_wfd_words(globals()[this+"_sample"], voiced = ("b", "d", "g"))
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc2 = lambda w : evaluate_wfd_words([w])#acceptor
sigstar2 = star(set(''.join(german_wfd_masked)), 5)

g2 = learn(german_wfd_masked + [""], k=2,m=2)

wrong2 = wrong(g2, acc2, sigstar2)

print(len(wrong2))
"""

# ## Experiment 2: Single vowel harmony without blocking

# ### Artificial grammar

# In[63]:


'''this = "mitsl4"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_vhnb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], single_harmony_no_blockers)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc4 = lambda w : harmonic_evaluator([w], single_harmony_no_blockers)#acceptor
sigstar4 = list(star(set(''.join(toy_vhnb)), 5))

g4 = learn(toy_vhnb + [""], k=2,m=2)

wrong4 = wrong(g4, acc4, sigstar4)

save(4, toy_vhnb, acc4, sigstar4, g4, wrong4)


# ### Simplified Finnish harmony

# In[64]:


"""'''this = "mitsl5"
globals()[this] = MITSL(polar = "n")
globals()[this].data = finnish_harmony_masked
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
globals()[this+"_sample"] = pickle.load(open(f'results_/{this}/sample', 'rb'))
harmonic_evaluator(globals()[this+"_sample"], front_harmony)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc5 = lambda w : harmonic_evaluator([w], front_harmony)#acceptor
sigstar5 = star(set(''.join(finnish_harmony_masked)), 5)

g5 = learn(finnish_harmony_masked + [""], k=2,m=2)

wrong5 = wrong(g5, acc5, sigstar5)

print(len(wrong5))"""

# ## Experiment 3: Single vowel harmony with blockers

# ### Artificial grammar

# In[65]:


'''this = "mitsl7"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_vhwb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], single_harmony_with_blockers)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc7 = lambda w : harmonic_evaluator([w], single_harmony_with_blockers)#acceptor
sigstar7 = list(star(set(''.join(toy_vhwb)), 5))

g7 = learn(toy_vhwb + [""], k=2,m=2)

wrong7 = wrong(g7, acc7, sigstar7)

save(7, toy_vhwb, acc7, sigstar7, g7, wrong7)


# ## Experiment 4: Two vowel harmonies, no blockers

# ### Artificial grammar

# In[66]:


'''this = "mitsl8"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_shnb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], double_harmony)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc8 = lambda w : harmonic_evaluator([w], double_harmony)#acceptor
sigstar8 = list(star(set(''.join(toy_shnb)), 5))

g8 = learn(toy_shnb + [""], k=2,m=2)

wrong8 = wrong(g8, acc8, sigstar8)

save(8, toy_shnb, acc8, sigstar8, g8, wrong8)


# ## Experiment 5: Two vowel harmonies with vowel blockers

# ### Artificial grammar

# In[67]:


'''this = "mitsl9"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_mhwb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], backness_and_rounding)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc9 = lambda w : harmonic_evaluator([w], backness_and_rounding)#acceptor
sigstar9 = list(star(set(''.join(toy_mhwb)), 5))

g9 = learn(toy_mhwb + [""], k=2,m=2)

wrong9 = wrong(g9, acc9, sigstar9)

save(9, toy_mhwb, acc9, sigstar9, g9, wrong9)


# ### Simplified Turkish harmony

# In[68]:


"""'''this = "mitsl10"
globals()[this] = MITSL(polar = "n")
globals()[this].data = turkish_harmony_masked
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], backness_and_rounding)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc10 = lambda w : harmonic_evaluator([w], backness_and_rounding)#acceptor
sigstar10 = star(set(''.join(turkish_harmony_masked)), 5)

g10 = learn(turkish_harmony_masked + [""], k=2,m=2)

wrong10 = wrong(g10, acc10, sigstar10)

print(len(wrong10))"""

# ## Experiment 6: Vowel harmony and consonant harmony, no blockers

# ### Artificial grammar

# In[69]:


'''this = "mitsl12"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_dhnb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], double_harmony_no_blockers)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc12 = lambda w : harmonic_evaluator([w], double_harmony_no_blockers)#acceptor
sigstar12 = list(star(set(''.join(toy_dhnb)), 5))

g12 = learn(toy_dhnb + [""], k=2,m=2)

wrong12 = wrong(g12, acc12, sigstar12)

save(12, toy_dhnb, acc12, sigstar12, g12, wrong12)


# ## Experiment 7: Vowel harmony and consonant harmony with blockers

# ### Artificial grammar

# In[70]:


'''this = "mitsl13"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_dhwb
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
harmonic_evaluator(globals()[this+"_sample"], double_harmony_with_blockers)
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc13 = lambda w : harmonic_evaluator([w], double_harmony_with_blockers)#acceptor
sigstar13 = list(star(set(''.join(toy_dhwb)), 5))

g13 = learn(toy_dhwb + [""], k=2,m=2)

wrong13 = wrong(g13, acc13, sigstar13)

save(13, toy_dhwb, acc13, sigstar13, g13, wrong13)


# ## Experiment 8: Unbounded tonal plateauing

# ### Artificial grammar

# In[71]:


'''this = "mitsl14"
globals()[this] = MITSL(polar = "n")
globals()[this].data = toy_utp
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
evaluate_utp_strings(globals()[this+"_sample"])
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("First 30 restrictions:", globals()[this].grammar[:30])'''


acc14 = lambda w : evaluate_utp_strings([w])#acceptor
sigstar14 = list(star(set(''.join(toy_utp)), 5))

g14 = learn(toy_utp + [""], k=2,m=2)

wrong14 = wrong(g14, acc14, sigstar14)

save(14, toy_utp, acc14, sigstar14, g14, wrong14)


# ## Experiment 9: First-last harmony

# ### Artificial grammar

# In[72]:


'''this = "mitsl15"
globals()[this] = MITSL(polar = "n")
globals()[this].data = first_last_data
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
evaluate_first_last_words(globals()[this+"_sample"])
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc15 = lambda w : evaluate_first_last_words([w])#acceptor
sigstar15 = list(star(set(''.join(first_last_data)), 5))

g15 = learn(first_last_data + [""], k=2,m=2)

wrong15 = wrong(g15, acc15, sigstar15)

save(15, first_last_data, acc15, sigstar15, g15, wrong15)


# ## Experiment 10: Two locally-driven long-distance assimilations (ITSL restrictions)

# ### Artificial grammar

# In[73]:


'''this = "mitsl16"
globals()[this] = MITSL(polar = "n")
globals()[this].data = assim_two
globals()[this].data.append("") # added to eliminate *>< on all tiers
globals()[this].extract_alphabet()
globals()[this].learn()
globals()[this+"_sample"] = globals()[this].generate_sample(n = 1000)
evaluate_mitsl_words(globals()[this+"_sample"])
print("--------------------------")
print("Generates such strings:", globals()[this+"_sample"][:15])
print("--------------------------")
print("Size of the grammar:", len(globals()[this].grammar))
print("--------------------------")
print("Grammars:", globals()[this].grammar)'''


acc16 = lambda w : evaluate_mitsl_words([w])#acceptor
sigstar16 = list(star(set(''.join(assim_two)), 5))

g16 = learn(assim_two + [""], k=2,m=2)

wrong16 = wrong(g16, acc16, sigstar16)

save(16, assim_two, acc16, sigstar16, g16, wrong16)


# In[74]:


acc = { #gather acceptor functions
    1:evaluate_wfd_words,
    4:lambda w : harmonic_evaluator(w, single_harmony_no_blockers),
    7:lambda w : harmonic_evaluator(w, single_harmony_with_blockers),
    8:lambda w : harmonic_evaluator(w, double_harmony),
    9:lambda w : harmonic_evaluator(w, backness_and_rounding),
    12:lambda w : harmonic_evaluator(w, double_harmony_no_blockers),
    13:lambda w : harmonic_evaluator(w, double_harmony_with_blockers),
    14:evaluate_utp_strings,
    15:evaluate_first_last_words,
    16:evaluate_mitsl_words
}

for i in [1, 4, 7, 8, 9, 12, 13, 14, 15, 16]: #for each experiment:
    wr = pickle.load(open(f'{i}/wrong', 'rb'))          #load the list of strings for which the learned grammar gave the wrong result
    sample = pickle.load(open(f'{i}/sample', 'rb'))     #load the sample it was trained on
    sigma = set(''.join(sample))                        #gather every character in the target language
    sigstar = list(star(sigma, 5))                      #generate every string up to length 5
    print(i, f'{len(wr)}/{len(sigstar)}', acc[i](wr))   #print the language#, the fraction of strings up to length 5 the learned grammar failed on, and whether these failed words were accepted by the original acceptor

#Here's the sample output from when I ran it:
'''
1 190/364 1.0
4 109/364 1.0
7 493/1365 1.0
8 213/3906 1.0
9 390/66430 1.0
12 143/1365 1.0
13 864/3906 1.0
14 7/63 1.0
15 70/364 1.0
16 30329/37449 1.0
'''

#this rightmost column result tells us the grammar is incomplete, but consistent - it only failed on words that it should have accepted (but didn't)

# In[75]:


#NEXT: what if we take these "failed" strings, and train the learner on them? If these languages are learnable by this algorithm, then it should converge on the target grammar, 

for i in [1, 4, 7, 8, 9, 12, 13, 14, 15, 16]:               #For each experiment:
                                                                        #load everything
    wr = pickle.load(open(f'{i}/wrong', 'rb')) #failed strings
    g = pickle.load(open(f'{i}/g', 'rb')) #grammar

                                                                        #somehow sigstar didn't pickle correctly, so we need to rebuild it
    sample = pickle.load(open(f'{i}/sample', 'rb'))
    sigma = set(''.join(sample))
    sigstar = list(star(sigma, 5))

    g = learn(wr, g=g)                                                  #learn on the missing samples

    accw = lambda w : acc[i]([w])                                       #converting the acceptor from the above cell (which takes a whole list as input) into an acceptor that wrong() can use, meaning it only takes one word at a time

    wr = wrong(g, accw, sigstar)                                        #test it on sigstar and generate the new list of misses

    print(i, wr)

#Here is the sample output from when I ran it:
'''
1 []
4 []
7 []
8 []
9 []
12 []
13 []
14 []
15 []
# Sadly, the Jupyter Kernel crashed after it spent over a day running experiment 16 
'''
