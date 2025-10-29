import requests
from bs4 import BeautifulSoup
import re

def get_h_index(scholar_url):
    """
    Scrape Google Scholar profile page and extract h-index.
    
    Args:
        scholar_url (str): URL of the Google Scholar profile page
        
    Returns:
        dict: Dictionary containing h-index and other citation metrics
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(scholar_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metrics_table = soup.find('table', {'id': 'gsc_rsb_st'})
        
        if not metrics_table:
            return {"error": "Could not find metrics table on the page"}
        
        metric_values = soup.find_all('td', class_='gsc_rsb_std')
        
        results = {}
        
        if len(metric_values) >= 6:
            results['citations_all'] = metric_values[0].get_text(strip=True)
            results['citations_recent'] = metric_values[1].get_text(strip=True)
            results['h_index_all'] = metric_values[2].get_text(strip=True)
            results['h_index_recent'] = metric_values[3].get_text(strip=True)
            results['i10_index_all'] = metric_values[4].get_text(strip=True)
            results['i10_index_recent'] = metric_values[5].get_text(strip=True)
        else:
            return {"error": f"Expected 6 metric values, found {len(metric_values)}"}
        
        name_elem = soup.find('div', {'id': 'gsc_prf_in'})
        if name_elem:
            results['name'] = name_elem.get_text(strip=True)
        
        return results
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def get_publications(scholar_url):
    """
    Scrape all publications from a Google Scholar profile page.
    
    Args:
        scholar_url (str): URL of the Google Scholar profile page
        
    Returns:
        list: List of dictionaries containing publication details
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Extract user ID from URL to construct the "show more" URL
        user_match = re.search(r'user=([^&]+)', scholar_url)
        if not user_match:
            return {"error": "Could not extract user ID from URL"}
        
        user_id = user_match.group(1)
        
        # Get language parameter if present
        lang_match = re.search(r'hl=([^&]+)', scholar_url)
        lang = lang_match.group(1) if lang_match else 'en'
        
        publications = []
        start = 0
        page_size = 100
        
        while True:
            # Construct URL with pagination
            url = f"https://scholar.google.de/citations?user={user_id}&hl={lang}&cstart={start}&pagesize={page_size}"
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all publication rows
            pub_rows = soup.find_all('tr', class_='gsc_a_tr')
            
            if not pub_rows:
                break
            
            for row in pub_rows:
                pub = {}
                
                # Extract title
                title_elem = row.find('a', class_='gsc_a_at')
                if title_elem:
                    pub['title'] = title_elem.get_text(strip=True)
                else:
                    pub['title'] = 'N/A'
                
                # Extract authors and venue
                authors_elem = row.find('div', class_='gs_gray')
                if authors_elem:
                    pub['authors'] = authors_elem.get_text(strip=True)
                else:
                    pub['authors'] = 'N/A'
                
                # Extract venue (second gs_gray div)
                venue_elems = row.find_all('div', class_='gs_gray')
                if len(venue_elems) > 1:
                    pub['venue'] = venue_elems[1].get_text(strip=True)
                else:
                    pub['venue'] = 'N/A'
                
                # Extract year
                year_elem = row.find('span', class_='gsc_a_h')
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    pub['year'] = year_text if year_text else 'N/A'
                else:
                    pub['year'] = 'N/A'
                
                # Extract citations
                citations_elem = row.find('a', class_='gsc_a_ac')
                if citations_elem:
                    citations_text = citations_elem.get_text(strip=True)
                    try:
                        pub['citations'] = int(citations_text) if citations_text else 0
                    except ValueError:
                        pub['citations'] = 0
                else:
                    pub['citations'] = 0
                
                publications.append(pub)
            
            # Check if there are more publications
            if len(pub_rows) < page_size:
                break
            
            start += page_size
        
        return publications
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def print_publications_sorted(publications):
    """
    Print publications sorted by number of citations (descending).
    
    Args:
        publications (list): List of publication dictionaries
    """
    if isinstance(publications, dict) and "error" in publications:
        print(f"Error: {publications['error']}")
        return
    
    # Sort by citations in descending order
    sorted_pubs = sorted(publications, key=lambda x: x['citations'], reverse=True)
    
    print(f"\n{'='*100}")
    print(f"PUBLICATIONS SORTED BY CITATIONS (Total: {len(sorted_pubs)})")
    print(f"{'='*100}\n")
    
    for i, pub in enumerate(sorted_pubs, 1):
        print(f"{i}. {pub['title']}")
        print(f"   Authors: {pub['authors']}")
        print(f"   Venue: {pub['venue']}")
        print(f"   Year: {pub['year']}")
        print(f"   Citations: {pub['citations']}")
        print()


def find_undercited_publications(publications, current_year=2025):
    """
    Find publications where citations < age in years.
    
    Args:
        publications (list): List of publication dictionaries
        current_year (int): Current year for age calculation
        
    Returns:
        list: List of undercited publications
    """
    if isinstance(publications, dict) and "error" in publications:
        return []
    
    undercited = []
    
    for pub in publications:
        year_str = pub.get('year', 'N/A')
        
        # Skip if year is not available or not a valid number
        if year_str == 'N/A' or not year_str.isdigit():
            continue
        
        year = int(year_str)
        age = current_year - year
        citations = pub.get('citations', 0)
        
        # Only consider publications at least 1 year old
        if age > 0 and citations < age:
            pub['age'] = age
            undercited.append(pub)
    
    return undercited


def print_undercited_publications(undercited_pubs):
    """
    Print publications that have been cited less than their age in years.
    
    Args:
        undercited_pubs (list): List of undercited publication dictionaries
    """
    if not undercited_pubs:
        print(f"\n{'='*100}")
        print("UNDERCITED PUBLICATIONS (Citations < Age in Years)")
        print(f"{'='*100}")
        print("\nNo undercited publications found.")
        return
    
    # Sort by how undercited they are (age - citations)
    sorted_undercited = sorted(undercited_pubs, 
                               key=lambda x: x['age'] - x['citations'], 
                               reverse=True)
    
    print(f"\n{'='*100}")
    print(f"UNDERCITED PUBLICATIONS (Citations < Age in Years) - Total: {len(sorted_undercited)}")
    print(f"{'='*100}\n")
    
    for i, pub in enumerate(sorted_undercited, 1):
        deficit = pub['age'] - pub['citations']
        print(f"{i}. {pub['title']}")
        print(f"   Authors: {pub['authors']}")
        print(f"   Venue: {pub['venue']}")
        print(f"   Year: {pub['year']} (Age: {pub['age']} years)")
        print(f"   Citations: {pub['citations']} (Deficit: {deficit} citations)")
        print()


# Example usage
if __name__ == "__main__":
    url = "https://scholar.google.de/citations?user=6ImtercAAAAJ&hl=de&oi=ao"
    
    print(f"Scraping Google Scholar profile: {url}\n")
    
    # Get h-index and metrics
    metrics = get_h_index(url)
    
    if "error" in metrics:
        print(f"Error getting metrics: {metrics['error']}")
    else:
        print("="*50)
        print("CITATION METRICS")
        print("="*50)
        if 'name' in metrics:
            print(f"Researcher: {metrics['name']}")
        print(f"\nCitations (All): {metrics.get('citations_all', 'N/A')}")
        print(f"Citations (Since 2020): {metrics.get('citations_recent', 'N/A')}")
        print(f"\nh-index (All): {metrics.get('h_index_all', 'N/A')}")
        print(f"h-index (Since 2020): {metrics.get('h_index_recent', 'N/A')}")
        print(f"\ni10-index (All): {metrics.get('i10_index_all', 'N/A')}")
        print(f"i10-index (Since 2020): {metrics.get('i10_index_recent', 'N/A')}")
    
    # Get all publications
    print("\nFetching publications...")
    publications = get_publications(url)
    
    # Print publications sorted by citations
    print_publications_sorted(publications)
    
    # Find and print undercited publications
    undercited = find_undercited_publications(publications, current_year=2025)
    print_undercited_publications(undercited)
    
    # Print summary statistics
    if isinstance(publications, list) and publications:
        total_citations = sum(pub['citations'] for pub in publications)
        avg_citations = total_citations / len(publications) if publications else 0
        
        print(f"{'='*100}")
        print("SUMMARY STATISTICS")
        print(f"{'='*100}")
        print(f"Total Publications: {len(publications)}")
        print(f"Total Citations: {total_citations}")
        print(f"Average Citations per Publication: {avg_citations:.2f}")
        print(f"Most Cited Publication: {publications[0]['citations']} citations" if publications else "N/A")
        print(f"Undercited Publications: {len(undercited)}")
