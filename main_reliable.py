"""
main_reliable.py - Streamlit UI for Footwear Promotional Intensity Analyzer
Clean version with no emojis - works with your parse_universal.py format
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io

# Import your scrapers
from scrape_reliable import scrape_website
from parse_universal import parse_products_universal

def main():
    st.set_page_config(page_title="Footwear Promotions Analyzer", page_icon="👟", layout="wide")

    st.title("Footwear Promotional Intensity Analyzer")
    st.markdown("Analyze discount rates and promotional intensity across footwear retailers")

    # Sidebar configuration
    with st.sidebar:
        st.header("Settings")

        st.subheader("Scraping Options")
        auto_paginate = st.checkbox("Auto-paginate", value=True,
                                    help="Automatically follow pagination to scrape multiple pages")
        max_pages = st.slider("Max pages", min_value=1, max_value=20, value=10,
                             help="Maximum number of pages to scrape")

        st.subheader("Display Options")
        show_all_products = st.checkbox("Show all products", value=True,
                                       help="Show all products, not just those on sale")

        st.markdown("---")
        st.markdown("### Supported Sites")
        st.markdown("""
        **Working Sites:**
        - Nike
        - Merrell
        - Wolverine
        - Saucony
        - Under Armour
        - ON Running
        - And more...
        
        All sites use proven Selenium scraper.
        Average time: 10-15 seconds per page.
        """)

    # Main content
    st.header("Enter Website URL")

    col1, col2 = st.columns([3, 1])

    with col1:
        url = st.text_input(
            "URL to analyze",
            placeholder="https://www.nike.com/w/sale-3yaep",
            help="Enter the full URL of the category or sale page"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        scrape_button = st.button("Analyze", type="primary", use_container_width=True)

    # Quick links
    with st.expander("Quick Links - Popular Footwear Sale Pages"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **Nike**
            - [Men's Sale](https://www.nike.com/w/sale-3yaep)
            - [Women's Sale](https://www.nike.com/w/womens-sale-5e1x6z3yaep)
            
            **Merrell**
            - [Men's Sale](https://www.merrell.com/US/en/sale-mens/)
            - [Women's Sale](https://www.merrell.com/US/en/sale-womens/)
            """)

        with col2:
            st.markdown("""
            **Wolverine**
            - [Men's Sale](https://www.wolverine.com/US/en/sale/mens/)
            - [Women's Sale](https://www.wolverine.com/US/en/sale/womens/)
            
            **Saucony**
            - [Sale](https://www.saucony.com/en/sale/)
            """)

        with col3:
            st.markdown("""
            **Under Armour**
            - [Outlet](https://www.underarmour.com/en-us/c/outlet/)
            
            **ON Running**
            - [Sale](https://www.on-running.com/en-us/sale)
            """)

    # Process scraping request
    if scrape_button and url:

        st.info("Using proven Selenium scraper")

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # SCRAPING
            status_text.text("Scraping website...")
            progress_bar.progress(20)

            html_content, metadata = scrape_website(
                url,
                use_bright_data=False,
                bright_data_auth=None,
                auto_paginate=auto_paginate,
                max_pages=max_pages
            )

            progress_bar.progress(50)

            if not html_content:
                st.error("Failed to scrape website. Please check the URL and try again.")
                if 'error' in metadata:
                    st.error(f"Error: {metadata['error']}")
                return

            # PARSING
            status_text.text("Parsing products...")
            progress_bar.progress(70)

            products, site_promotions = parse_products_universal(html_content, url)
            progress_bar.progress(90)

            if not products:
                st.warning("No products found. This could mean:")
                st.markdown("""
                - The site uses heavy JavaScript that isn't loading
                - Bot detection is blocking the scraper
                - The page structure is different than expected
                - No products are currently listed on this page
                """)

                # Show metadata for debugging
                with st.expander("Debug Information"):
                    st.write("**Scraping Metadata:**")
                    st.json(metadata)
                    st.write(f"**HTML Length:** {len(html_content):,} bytes")
                    st.write(f"**Pages Scraped:** {metadata.get('pages_scraped', 0)}")

                return

            # ANALYSIS
            status_text.text("Analyzing promotions...")

            # Create DataFrame
            df = pd.DataFrame(products)

            # Calculate on_sale status based on discount
            df['on_sale'] = df['Discount %'].apply(lambda x: x != 'N/A' and x != '0.0%')
            df['discount_float'] = df['Discount %'].apply(
                lambda x: float(x.replace('%', '')) if x not in ['N/A', ''] else 0.0
            )

            # Filter for display
            if not show_all_products:
                df_display = df[df['on_sale'] == True].copy()
            else:
                df_display = df.copy()

            progress_bar.progress(100)
            status_text.text("Analysis complete!")

            # RESULTS
            st.success(f"Successfully analyzed {len(products)} products!")

            # Key Metrics
            st.header("Key Metrics")

            col1, col2, col3, col4 = st.columns(4)

            total_products = len(df)
            on_sale_products = len(df[df['on_sale'] == True])
            promo_intensity = (on_sale_products / total_products * 100) if total_products > 0 else 0

            sale_products = df[df['on_sale'] == True]
            if len(sale_products) > 0:
                avg_discount = sale_products['discount_float'].mean()
            else:
                avg_discount = 0

            with col1:
                st.metric("Total Products", f"{total_products:,}")

            with col2:
                st.metric("On Sale", f"{on_sale_products:,}")

            with col3:
                st.metric("Promo Intensity", f"{promo_intensity:.1f}%")

            with col4:
                st.metric("Avg Discount", f"{avg_discount:.1f}%")

            # Site-wide promotions
            if site_promotions:
                st.header("Site-Wide Promotions")
                for promo in site_promotions:
                    st.info(promo)

            # Products table
            st.header("Products")
            display_columns = ['Product Name', 'Original Price', 'Sale Price', 'Discount %', 'Brand']
            available_columns = [col for col in display_columns if col in df_display.columns]
            df_show = df_display[available_columns].copy()

            st.dataframe(
                df_show,
                use_container_width=True,
                height=400
            )

            # Export options
            st.header("Export Data")

            col1, col2 = st.columns(2)

            with col1:
                # CSV export
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"footwear_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            with col2:
                # Excel export
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Products')

                    # Add summary sheet
                    summary_data = {
                        'Metric': ['Total Products', 'On Sale', 'Promotional Intensity', 'Average Discount'],
                        'Value': [total_products, on_sale_products, f"{promo_intensity:.1f}%", f"{avg_discount:.1f}%"]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')

                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name=f"footwear_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Metadata
            with st.expander("Scraping Details"):
                st.write(f"**URL:** {url}")
                st.write(f"**Pages Scraped:** {metadata.get('pages_scraped', 0)}")
                st.write(f"**HTML Size:** {len(html_content):,} bytes")
                st.write(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)

    elif scrape_button and not url:
        st.warning("Please enter a URL to analyze")

    # Optional: provide the share instructions at the bottom
    st.markdown("---")
    st.markdown(
        "To share your analysis, deploy this app on Streamlit Cloud or another host and send users the link. "
        "They can enter any site above, run analysis, and download results."
    )

if __name__ == "__main__":
    main()
